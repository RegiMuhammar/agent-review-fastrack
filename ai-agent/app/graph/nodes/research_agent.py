"""
research_agent.py — Research Agent Node (Fase 2+3)
==================================================
Node khusus untuk doc_type="research".
Membangun agent_context dari metadata terstruktur (title, abstract, keywords)
ditambah profil dokumen (domain, paper_type, retrieval_focus) dan
potongan dokumen yang lebih terarah, bukan raw_markdown[:6000] mentah.

Perbedaan utama dengan essay_agent:
- Context dibangun dari metadata + profil + excerpt berbasis section.
- search_queries disiapkan sebagai placeholder untuk Fase 4.
- Output state siap digunakan oleh node search & retrieval di fase berikutnya.

Flow: extract → metadata_extract → document_profile → research_agent → score → generate
"""

from app.graph.state import ReviewEngineState


# ── HELPERS ──────────────────────────────────────────────────────────────────

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
        print(f"[research_agent][log_step] log gagal (diabaikan): {exc}")


def _build_metadata_block(state: ReviewEngineState) -> str:
    """Bangun blok metadata terstruktur untuk context LLM."""
    title = state.get("title") or "Tidak tersedia"
    abstract = state.get("abstract") or ""
    authors = state.get("authors") or []
    keywords = state.get("keywords") or []

    # Profiling data (Fase 3)
    domain = state.get("domain") or ""
    sub_domain = state.get("sub_domain") or ""
    paper_type = state.get("paper_type") or ""
    retrieval_focus = state.get("retrieval_focus") or []

    lines = [
        "PAPER METADATA",
        f"- Title: {title}",
    ]

    if authors:
        lines.append(f"- Authors: {', '.join(authors)}")

    if keywords:
        lines.append(f"- Keywords: {', '.join(keywords)}")

    if domain:
        domain_str = f"{domain}/{sub_domain}" if sub_domain else domain
        lines.append(f"- Domain: {domain_str}")

    if paper_type:
        lines.append(f"- Paper type: {paper_type}")

    if retrieval_focus:
        lines.append(f"- Retrieval focus: {', '.join(retrieval_focus)}")

    if abstract:
        lines.append(f"\nABSTRACT\n{abstract}")

    return "\n".join(lines)


def _build_evidence_excerpt(state: ReviewEngineState, max_chars: int = 4000) -> str:
    """
    Bangun excerpt dokumen yang lebih terarah dibanding raw_markdown[:6000].

    Strategi:
    - Ambil document_head (~3500 char) — biasanya berisi intro & method awal
    - Ambil document_tail (~1500 char) — biasanya berisi conclusion & references
    - Total target: ~4000 karakter (lebih ringkas dari 6000 kasar)

    Di fase berikutnya (Fase 7 - evidence_select), ini akan digantikan
    oleh section-based evidence extraction yang lebih presisi.
    """
    head = state.get("document_head") or ""
    tail = state.get("document_tail") or ""

    # Jika document_head/tail belum tersedia, fallback ke raw_markdown
    if not head and not tail:
        raw = state.get("raw_markdown", "")
        return raw[:max_chars] if raw else ""

    # Gabungkan head + tail, dengan batas total
    if head and tail and head != tail:
        # Pastikan tidak overlap (tail mungkin sudah termasuk di head untuk dokumen pendek)
        combined = head.rstrip() + "\n\n[...]\n\n" + tail.lstrip()
        return combined[:max_chars]

    return (head or tail)[:max_chars]


# ── NODE UTAMA ───────────────────────────────────────────────────────────────

async def research_agent_node(state: ReviewEngineState) -> dict:
    """
    LangGraph node: Menyiapkan context review untuk dokumen research.

    Berbeda dengan essay_agent yang hanya potong raw_markdown[:6000],
    research_agent membangun context terstruktur dari:
    1. Metadata (title, abstract, authors, keywords)
    2. Excerpt dokumen (head + tail, bukan potongan kasar)

    Input dari state:
        - title, abstract, authors, keywords (dari metadata_extract)
        - domain, sub_domain, paper_type, retrieval_focus (dari document_profile)
        - document_head, document_tail (dari metadata_extract)
        - raw_markdown (fallback jika head/tail belum tersedia)
        - analysis_id (untuk logging)

    Output (di-merge ke state):
        - agent_context : context terstruktur untuk LLM scoring
        - search_queries : placeholder (akan diisi di Fase 4)
    """
    analysis_id = state.get("analysis_id", "unknown")

    print(f"\n[research_agent] Memulai persiapan context research...")
    _safe_log(analysis_id, "preparing", "processing", "Menyiapkan analisis research paper...")

    # ─── Bangun context terstruktur ──────────────────────────────────────
    metadata_block = _build_metadata_block(state)
    evidence_excerpt = _build_evidence_excerpt(state)

    # Rakit agent_context format yang akan dikirim ke score node
    agent_context = f"""{metadata_block}

SELECTED DOCUMENT EXCERPT
{evidence_excerpt}
""".strip()

    # search_queries diisi oleh retrieval_prep (Fase 4), bukan di sini
    search_queries: dict[str, list[str]] = {}

    context_len = len(agent_context)
    print(f"[research_agent] Context dibangun: {context_len} chars")
    print(f"[research_agent] Metadata: title='{(state.get('title') or '')[:60]}'")
    print(f"[research_agent] Profile: {state.get('domain', '?')}/{state.get('sub_domain', '?')} ({state.get('paper_type', '?')})")
    print(f"[research_agent] Abstract: {len(state.get('abstract') or '')} chars")
    print(f"[research_agent] Search queries: {len(search_queries)} (placeholder)")

    _safe_log(analysis_id, "preparing", "done", f"Konteks research siap ({context_len} chars)")

    return {
        "agent_context": agent_context,
        "search_queries": search_queries,
    }
