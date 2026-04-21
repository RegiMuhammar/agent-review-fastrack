"""
generate.py — Generate Final Report Node (Fase 9)
===================================================
Menyusun `final_result` yang informatif untuk frontend dan callback Laravel.

Enrichment untuk research:
- Metadata penting (authors, keywords, domain, paper_type)
- Top references dari pipeline search
- Extracted strengths & improvements dari dimension feedback
- Profile data (domain, sub_domain, paper_type)

Keamanan:
- TIDAK menyertakan `review_context`, `raw_markdown`, atau `agent_context`
- Hanya data yang berguna untuk frontend/display
"""

import re

from app.graph.state import ReviewEngineState


STRENGTH_CUES = [
    "kuat",
    "solid",
    "jelas",
    "baik",
    "relevan",
    "menjanjikan",
    "unik",
    "terukur",
]

IMPROVEMENT_CUES = [
    "namun",
    "tetapi",
    "perlu",
    "masih",
    "belum",
    "sebaiknya",
    "dapat ditingkatkan",
    "butuh",
    "risiko",
]


def _safe_log(analysis_id: str, step: str, status: str, message: str) -> None:
    """Helper untuk logging progres ke Laravel node Generate"""
    try:
        import asyncio
        from app.services.laravel_client import log_step
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(log_step(analysis_id, step, status, message))
        except RuntimeError:
            asyncio.run(log_step(analysis_id, step, status, message))
    except Exception as exc:
        print(f"[generate_node][log_step] log gagal: {exc}")


def _clean_feedback_text(text: str) -> str:
    return " ".join((text or "").strip().split())


def _extract_positive_clause(feedback: str) -> str:
    feedback = _clean_feedback_text(feedback)
    if not feedback:
        return ""

    parts = re.split(r"\b(?:Namun|Tetapi|Akan tetapi|Meski demikian|Walau demikian)\b", feedback, maxsplit=1)
    clause = parts[0].strip(" .:-")
    return clause or feedback


def _extract_improvement_clause(feedback: str) -> str:
    feedback = _clean_feedback_text(feedback)
    if not feedback:
        return ""

    match = re.search(
        r"\b(?:Namun|Tetapi|Akan tetapi|Meski demikian|Walau demikian|perlu|masih|belum|sebaiknya|butuh)\b.*",
        feedback,
        re.IGNORECASE,
    )
    if match:
        return match.group(0).strip(" .:-")
    return feedback


def _extract_strengths_improvements(dimensions: list[dict]) -> tuple[list[str], list[str]]:
    """
    Extract strengths dan improvements dari dimensi feedback.

    Strategi:
    - strengths diambil dari dimensi skor tinggi dengan clause positif
    - improvements diambil dari dimensi skor terendah atau feedback yang memuat cue perbaikan
    - pastikan minimal ada 2 improvement bila feedback tersedia
    """
    strengths = []
    improvements = []
    ranked_dimensions = []

    for dim in dimensions:
        key = dim.get("key", "")
        try:
            score = float(dim.get("score", 0))
        except (TypeError, ValueError):
            score = 0.0
        feedback = _clean_feedback_text(dim.get("feedback", ""))
        label = dim.get("label") or dim.get("name") or key.replace("_", " ").title()
        if not feedback:
            continue
        ranked_dimensions.append({
            "label": label,
            "score": score,
            "feedback": feedback,
        })

    if not ranked_dimensions:
        return strengths, improvements

    for dim in sorted(ranked_dimensions, key=lambda item: item["score"], reverse=True):
        positive_clause = _extract_positive_clause(dim["feedback"])
        lowered = positive_clause.lower()
        if dim["score"] >= 7.5 or any(cue in lowered for cue in STRENGTH_CUES):
            strengths.append(f"{dim['label']}: {positive_clause[:300]}")
        if len(strengths) >= 3:
            break

    improvement_candidates = []
    for dim in sorted(ranked_dimensions, key=lambda item: item["score"]):
        lowered = dim["feedback"].lower()
        if dim["score"] <= 7.9 or any(cue in lowered for cue in IMPROVEMENT_CUES):
            clause = _extract_improvement_clause(dim["feedback"])
            improvement_candidates.append(f"{dim['label']}: {clause[:300]}")

    for item in improvement_candidates:
        if item not in improvements:
            improvements.append(item)
        if len(improvements) >= 3:
            break

    if len(improvements) < 2:
        for dim in sorted(ranked_dimensions, key=lambda item: item["score"]):
            fallback = f"{dim['label']}: {_extract_improvement_clause(dim['feedback'])[:300]}"
            if fallback not in improvements:
                improvements.append(fallback)
            if len(improvements) >= 2:
                break

    return strengths[:3], improvements[:3]


def _build_references_output(top_references: list[dict]) -> list[dict]:
    """
    Format top_references untuk output frontend.
    Hanya field yang berguna, tanpa snippet panjang atau internal scores.
    """
    refs_output = []
    for ref in top_references[:5]:
        refs_output.append({
            "title": ref.get("title", "Untitled"),
            "authors": ref.get("authors", [])[:4],
            "year": ref.get("year"),
            "url": ref.get("url", ""),
            "source": ref.get("source", ""),
        })
    return refs_output


def _build_bizplan_snapshot(state: ReviewEngineState) -> dict:
    return {
        "company_name": state.get("company_name"),
        "industry": state.get("industry"),
        "geography": state.get("geography"),
        "business_stage": state.get("business_stage"),
        "funding_ask": state.get("funding_ask"),
        "target_customer": state.get("target_customer", []),
        "revenue_model": state.get("revenue_model", []),
    }


async def generate_node(state: ReviewEngineState) -> dict:
    """
    Node akhir: Menyusun final_result yang informatif.
    
    Output berbeda per doc_type:
    - Essay/bizplan: basic (title, score, dimensions, feedback)
    - Research: enriched (+ metadata, profile, references, strengths/improvements)
    """
    analysis_id = state.get("analysis_id")
    doc_type = state.get("doc_type", "essay")

    print("\n[generate_node] Menyusun laporan akhir...")
    _safe_log(analysis_id, "generating", "processing", "Menyusun laporan evaluasi akhir...")

    dimensions = state.get("dimensions_feedback", [])

    # Extract strengths & improvements dari dimensi
    strengths, improvements = _extract_strengths_improvements(dimensions)

    # ─── Base result (semua doc_type) ─────────────────────────────────────
    final_result = {
        "analysis_id": analysis_id,
        "doc_type": doc_type,
        "title": state.get("title") or "Dokumen Tanpa Judul",
        "page_count": state.get("page_count", 0),
        "score_overall": state.get("score_overall", 0.0),
        "summary": state.get("summary", ""),
        "dimensions": dimensions,
        "overall_feedback": state.get("overall_feedback", ""),
        "strengths": strengths,
        "improvements": improvements,
    }

    # ─── Enriched metadata (Fase 9 - Always include if available) ─────────
    final_result["metadata"] = {
        "authors": state.get("authors", []),
        "keywords": state.get("keywords", []),
        "abstract": (state.get("abstract") or "")[:500],
        "company_name": state.get("company_name"),
        "industry": state.get("industry"),
        "geography": state.get("geography"),
        "business_stage": state.get("business_stage"),
    }

    # ─── References (Now enabled for all doc_types!) ──────────────────────
    top_refs = state.get("top_references") or []
    final_result["references"] = _build_references_output(top_refs)

    # ─── Research specific enrichment (Profile) ───────────────────────────
    if doc_type == "research":
        final_result["profile"] = {
            "domain": state.get("domain"),
            "sub_domain": state.get("sub_domain"),
            "paper_type": state.get("paper_type"),
            "retrieval_focus": state.get("retrieval_focus", []),
        }
        
        # Stats pipeline
        search_results_count = len(state.get("search_results") or [])
        evidence_chunks_count = len(state.get("evidence_chunks") or [])
        final_result["pipeline_stats"] = {
            "search_results_total": search_results_count,
            "references_selected": len(top_refs),
            "evidence_chunks": evidence_chunks_count,
        }
    elif doc_type == "bizplan":
        final_result["profile"] = {
            "domain": state.get("domain"),
            "sub_domain": state.get("sub_domain"),
            "target_customer": state.get("target_customer", []),
            "funding_ask": state.get("funding_ask"),
            "traction_signals": state.get("traction_signals", []),
            "pricing_signals": state.get("pricing_signals", []),
        }
        final_result["business_snapshot"] = _build_bizplan_snapshot(state)
        final_result["financial_metrics"] = state.get("financial_metrics") or {
            "pricing": state.get("pricing", []),
            "revenue_model": state.get("revenue_model", []),
            "cac": None,
            "ltv": None,
            "gross_margin": None,
            "burn_rate": state.get("burn_rate"),
            "runway_months": state.get("runway_months"),
            "break_even_timeline": state.get("break_even_timeline"),
            "funding_needed": state.get("funding_ask"),
        }
        final_result["financial_red_flags"] = state.get("financial_red_flags", [])
        final_result["unit_economics_signals"] = state.get("unit_economics_signals") or {}
        final_result["market_validation"] = state.get("market_validation") or {
            "status": state.get("market_validation_status"),
            "market_size_summary": "",
            "evidence": [],
        }
        final_result["competition_insights"] = state.get("competition_insights") or {
            "direct_competitors": [],
            "substitutes": [],
            "key_risk": "",
        }
        final_result["market_red_flags"] = state.get("market_red_flags", [])
    else:
        # Essay basic profile
        final_result["profile"] = {
            "domain": state.get("domain"),
            "sub_domain": state.get("sub_domain"),
        }

    _safe_log(analysis_id, "generating", "done", "Laporan evaluasi berhasil disusun.")
    print(f"[generate_node] Selesai — score: {final_result['score_overall']}/10, "
          f"strengths: {len(strengths)}, improvements: {len(improvements)}\n")

    return {"final_result": final_result}
