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

def _build_references_block(state: ReviewEngineState) -> str:
    """Bangun blok referensi dari top_references (Fase 6)."""
    top_refs = state.get("top_references") or []
    if not top_refs:
        return ""

    lines = ["RELEVANT REFERENCES"]
    for i, ref in enumerate(top_refs[:5], 1):
        title = ref.get("title", "Untitled")
        source = ref.get("source", "?")
        year = ref.get("year", "N/A")
        authors = ref.get("authors", [])
        snippet = (ref.get("snippet") or "")[:200]
        score = ref.get("relevance_score", 0)

        author_str = ", ".join(authors[:3]) if authors else "Unknown"
        lines.append(
            f"[{i}] {title}\n"
            f"    Authors: {author_str} | Year: {year} | Source: {source} | Relevance: {score:.2f}\n"
            f"    {snippet}"
        )

    return "\n".join(lines)


async def research_agent_node(state: ReviewEngineState) -> dict:
    """
    LangGraph node: Menyiapkan context review untuk dokumen research.

    Berbeda dengan essay_agent yang hanya potong raw_markdown[:6000],
    research_agent membangun context terstruktur dari:
    1. Metadata (title, abstract, authors, keywords, domain, paper_type)
    2. Excerpt dokumen (head + tail, bukan potongan kasar)
    3. Top references dari search & rank (Fase 5-6)

    Input dari state:
        - title, abstract, authors, keywords (dari metadata_extract)
        - domain, sub_domain, paper_type, retrieval_focus (dari document_profile)
        - document_head, document_tail (dari metadata_extract)
        - top_references (dari search_rank, Fase 6)
        - raw_markdown (fallback jika head/tail belum tersedia)
        - analysis_id (untuk logging)

    Output (di-merge ke state):
        - agent_context : context terstruktur untuk LLM scoring
    """
    analysis_id = state.get("analysis_id", "unknown")

    print(f"\n[research_agent] Memulai persiapan context research...")
    _safe_log(analysis_id, "preparing", "processing", "Menyiapkan analisis research paper...")

    # ─── Bangun context terstruktur ──────────────────────────────────────
    metadata_block = _build_metadata_block(state)
    evidence_excerpt = _build_evidence_excerpt(state)
    references_block = _build_references_block(state)

    # Rakit agent_context
    sections = [metadata_block, f"SELECTED DOCUMENT EXCERPT\n{evidence_excerpt}"]
    if references_block:
        sections.append(references_block)

    agent_context = "\n\n".join(sections)

    top_refs_count = len(state.get("top_references") or [])
    context_len = len(agent_context)
    print(f"[research_agent] Context dibangun: {context_len} chars")
    print(f"[research_agent] Metadata: title='{(state.get('title') or '')[:60]}'")
    print(f"[research_agent] Profile: {state.get('domain', '?')}/{state.get('sub_domain', '?')} ({state.get('paper_type', '?')})")
    print(f"[research_agent] References: {top_refs_count} referensi dalam context")

    _safe_log(analysis_id, "preparing", "done", f"Konteks research siap ({context_len} chars, {top_refs_count} refs)")

    return {
        "agent_context": agent_context,
    }

