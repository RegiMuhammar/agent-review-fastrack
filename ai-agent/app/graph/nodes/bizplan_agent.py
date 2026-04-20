"""
bizplan_agent.py - Sintesis context untuk business plan
=======================================================
Menyiapkan context yang lebih tajam untuk scoring business plan.

Strategi:
- Ekstrak section penting bisnis jika header terdeteksi.
- Fallback ke excerpt head/middle/tail jika struktur dokumen lemah.
- Gabungkan snapshot metadata + evidence bisnis dalam format ringkas.
"""

from __future__ import annotations

import re

from app.graph.state import ReviewEngineState


SECTION_PATTERNS = {
    "problem_solution": [
        r"(?:^|\n)\s*#{1,3}\s*\*{0,2}\s*(?:problem|problem statement|pain point|masalah|latar belakang|solution|solusi)\s*\*{0,2}\s*(?:\n|$)",
        r"(?:^|\n)\s*#{1,3}\s*\*{0,2}\s*(?:executive summary|ringkasan eksekutif)\s*\*{0,2}\s*(?:\n|$)",
    ],
    "market": [
        r"(?:^|\n)\s*#{1,3}\s*\*{0,2}\s*(?:market|market analysis|target market|customer segment|customers?|pasar|analisis pasar|segmentasi)\s*\*{0,2}\s*(?:\n|$)",
    ],
    "business_model": [
        r"(?:^|\n)\s*#{1,3}\s*\*{0,2}\s*(?:business model|revenue|monetization|pricing|go to market|model bisnis|pendapatan|harga)\s*\*{0,2}\s*(?:\n|$)",
    ],
    "competition": [
        r"(?:^|\n)\s*#{1,3}\s*\*{0,2}\s*(?:competition|competitor|competitive|moat|competitif|kompetitor|pesaing)\s*\*{0,2}\s*(?:\n|$)",
    ],
    "team": [
        r"(?:^|\n)\s*#{1,3}\s*\*{0,2}\s*(?:team|founders?|management|operational plan|execution|tim|pendiri|operasional|eksekusi)\s*\*{0,2}\s*(?:\n|$)",
    ],
    "financial": [
        r"(?:^|\n)\s*#{1,3}\s*\*{0,2}\s*(?:financial|finance|projection|projections|funding|unit economics|keuangan|proyeksi|pendanaan)\s*\*{0,2}\s*(?:\n|$)",
    ],
}

SECTION_BUDGETS = {
    "problem_solution": 900,
    "market": 900,
    "business_model": 850,
    "competition": 700,
    "team": 600,
    "financial": 750,
}

NEXT_SECTION_PATTERN = re.compile(
    r"\n\s*#{1,3}\s*\*{0,2}\s*(?:\d+[\.\)]?\s*)?[A-Za-z]",
    re.MULTILINE,
)


def _safe_log(analysis_id: str, step: str, status: str, message: str) -> None:
    """Logging ke Laravel secara best-effort."""
    try:
        import asyncio
        from app.services.laravel_client import log_step

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(log_step(analysis_id, step, status, message))
        except RuntimeError:
            asyncio.run(log_step(analysis_id, step, status, message))
    except Exception as exc:
        print(f"[bizplan_agent][log_step] log gagal (diabaikan): {exc}")


def _find_section(text: str, section_name: str) -> tuple[int, int] | None:
    for pattern in SECTION_PATTERNS.get(section_name, []):
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            return match.start(), match.end()
    return None


def _extract_section_content(text: str, section_name: str, max_chars: int) -> str | None:
    pos = _find_section(text, section_name)
    if pos is None:
        return None

    remaining = text[pos[1] :]
    next_section = NEXT_SECTION_PATTERN.search(remaining)
    content = remaining[: next_section.start()] if next_section else remaining
    content = content.strip()
    if not content:
        return None

    if len(content) > max_chars:
        truncated = content[:max_chars]
        last_period = max(truncated.rfind("."), truncated.rfind("\n"))
        content = truncated[: last_period + 1] if last_period > max_chars * 0.5 else truncated + "..."

    return content if len(content) >= 60 else None


def _extract_bizplan_chunks(raw_markdown: str) -> list[dict]:
    chunks: list[dict] = []
    for section_name, budget in SECTION_BUDGETS.items():
        content = _extract_section_content(raw_markdown, section_name, budget)
        if content:
            chunks.append({"section": section_name, "content": content, "chars": len(content)})
    return chunks


def _fallback_chunks(state: ReviewEngineState) -> list[dict]:
    raw = state.get("raw_markdown") or ""
    head = state.get("document_head") or ""
    tail = state.get("document_tail") or ""

    if raw:
        chunks = [
            {"section": "overview", "content": raw[:2200].strip(), "chars": min(len(raw), 2200)},
        ]
        if len(raw) > 5000:
            middle_start = max(len(raw) // 2 - 700, 0)
            chunks.append({"section": "operations", "content": raw[middle_start:middle_start + 1400].strip(), "chars": 1400})
        if len(raw) > 2600:
            chunks.append({"section": "closing", "content": raw[-1200:].strip(), "chars": 1200})
        return chunks

    chunks = []
    if head:
        chunks.append({"section": "overview", "content": head[:2200], "chars": min(len(head), 2200)})
    if tail:
        chunks.append({"section": "closing", "content": tail[:1200], "chars": min(len(tail), 1200)})
    return chunks


def _build_snapshot(state: ReviewEngineState) -> str:
    title = state.get("title") or "Business Plan"
    keywords = state.get("keywords") or []
    year = state.get("year") or "N/A"
    company_name = state.get("company_name") or title
    industry = state.get("industry") or "Tidak diketahui"
    geography = state.get("geography") or "Tidak diketahui"
    business_stage = state.get("business_stage") or "Tidak diketahui"
    funding_ask = state.get("funding_ask") or "Tidak disebutkan"
    target_customer = state.get("target_customer") or []
    revenue_model = state.get("revenue_model") or []
    pricing = state.get("pricing") or []
    runway_months = state.get("runway_months")
    break_even_timeline = state.get("break_even_timeline") or "Tidak disebutkan"
    financial_red_flags = state.get("financial_red_flags") or []
    market_validation_status = state.get("market_validation_status") or "belum tersedia"
    competition_insights = state.get("competition_insights") or {}
    competitors = competition_insights.get("direct_competitors") or []
    market_validation = state.get("market_validation") or {}
    market_summary = market_validation.get("market_size_summary") or ""

    lines = [
        "RINGKASAN BUSINESS PLAN",
        f"- Judul: {title}",
        f"- Nama usaha/perusahaan: {company_name}",
        f"- Tahun: {year}",
        f"- Industri: {industry}",
        f"- Geografi: {geography}",
        f"- Tahap bisnis: {business_stage}",
        f"- Pendanaan yang dicari: {funding_ask}",
        f"- Target pelanggan: {', '.join(target_customer) if target_customer else 'Belum jelas'}",
        f"- Model pendapatan: {', '.join(revenue_model) if revenue_model else 'Belum jelas'}",
        f"- Sinyal harga: {', '.join(pricing[:2]) if pricing else 'Belum jelas'}",
        f"- Runway: {runway_months} bulan" if runway_months is not None else "- Runway: Belum dapat diestimasi",
        f"- Break-even: {break_even_timeline}",
        f"- Status validasi pasar eksternal: {market_validation_status}",
        f"- Kompetitor teridentifikasi: {', '.join(competitors[:3]) if competitors else 'Belum teridentifikasi'}",
    ]
    if keywords:
        lines.append(f"- Kata kunci: {', '.join(keywords[:6])}")
    if financial_red_flags:
        lines.append(f"- Red flag finansial: {', '.join(financial_red_flags[:3])}")
    if market_summary:
        lines.append(f"- Ringkasan pasar eksternal: {market_summary}")
    return "\n".join(lines)


def _format_section_label(name: str) -> str:
    labels = {
        "problem_solution": "MASALAH & SOLUSI",
        "market": "PASAR",
        "business_model": "MODEL BISNIS",
        "competition": "KOMPETISI",
        "team": "TIM & EKSEKUSI",
        "financial": "KEUANGAN",
        "overview": "GAMBARAN UMUM",
        "operations": "OPERASI",
        "closing": "PENUTUP",
    }
    return labels.get(name, name.replace("_", " ").upper())


async def bizplan_agent_node(state: ReviewEngineState) -> dict:
    """
    Bangun context final untuk scoring business plan.

    Output:
    - agent_context: context ringkas berbasis section bisnis
    - evidence_chunks: chunk yang berhasil dipilih untuk jalur bizplan
    """
    analysis_id = state.get("analysis_id", "unknown")
    raw_markdown = state.get("raw_markdown") or ""

    print("\n[bizplan_agent] Menyiapkan context business plan...")
    _safe_log(analysis_id, "synthesis", "processing", "Menyusun context business plan yang lebih terarah...")

    chunks = _extract_bizplan_chunks(raw_markdown) if raw_markdown else []
    extraction_method = "section-based"
    if len(chunks) < 2:
        chunks = _fallback_chunks(state)
        extraction_method = "fallback"

    snapshot = _build_snapshot(state)
    evidence_lines = ["BUSINESS PLAN EVIDENCE"]
    for chunk in chunks:
        evidence_lines.append(f"[{_format_section_label(chunk['section'])}]\n{chunk['content']}")

    guidance = (
        "Fokus evaluasi pada problem-solution fit, ukuran pasar, model bisnis, "
        "keunggulan kompetitif, kesiapan eksekusi, dan kelayakan finansial."
    )

    market_validation = state.get("market_validation") or {}
    competition_insights = state.get("competition_insights") or {}
    market_red_flags = state.get("market_red_flags") or []
    external_market_evidence = state.get("external_market_evidence") or []
    competitive_evidence = state.get("competitive_evidence") or []

    market_block_lines = ["VALIDASI PASAR EKSTERNAL"]
    market_block_lines.append(f"- Status: {state.get('market_validation_status') or 'belum tersedia'}")
    market_summary = market_validation.get("market_size_summary") or ""
    if market_summary:
        market_block_lines.append(f"- Ringkasan pasar: {market_summary}")
    competitors = competition_insights.get("direct_competitors") or []
    if competitors:
        market_block_lines.append(f"- Kompetitor langsung: {', '.join(competitors[:4])}")
    key_risk = competition_insights.get("key_risk") or ""
    if key_risk:
        market_block_lines.append(f"- Risiko kompetisi: {key_risk}")
    if market_red_flags:
        market_block_lines.append(f"- Red flag pasar: {', '.join(market_red_flags[:3])}")
    for item in external_market_evidence[:2]:
        market_block_lines.append(f"[PASAR] {item.get('title', 'Tanpa judul')} - {item.get('snippet', '')}")
    for item in competitive_evidence[:2]:
        market_block_lines.append(f"[KOMPETISI] {item.get('title', 'Tanpa judul')} - {item.get('snippet', '')}")

    market_block = "\n".join(market_block_lines)

    evidence_lines[0] = "EVIDENSI BUSINESS PLAN"
    agent_context = "\n\n".join([snapshot, guidance, market_block, "\n\n".join(evidence_lines)])

    print(
        f"[bizplan_agent] Context siap: {len(agent_context)} chars | "
        f"chunks: {len(chunks)} | method: {extraction_method}"
    )
    _safe_log(
        analysis_id,
        "synthesis",
        "done",
        f"Context business plan siap ({len(chunks)} chunks, via {extraction_method})",
    )

    return {
        "agent_context": agent_context,
        "evidence_chunks": chunks,
    }
