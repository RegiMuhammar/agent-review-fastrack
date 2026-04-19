"""
evidence_select.py - Evidence Selection Node (Fase 7)
=====================================================
Membangun review_context yang tajam dan ringkas untuk LLM scoring.

Strategi evidence extraction:
1. Section detection via regex pada raw_markdown
   - Prioritas: Abstract, Introduction, Method, Results, Conclusion
   - Handle format pymupdf4llm: ## **1 Introduction**, ## I. INTRODUCTION
2. Jika section parsing gagal, fallback ke head/middle/tail excerpt
3. Gabungkan evidence chunks dengan metadata + top_references
4. Hasilkan review_context yang siap dikirim ke score node

Target ukuran review_context: ~4000-6000 chars (vs raw_markdown 50K+)

Flow: ... -> search_rank -> evidence_select -> research_agent -> score -> ...
"""

import re
import logging

from app.graph.state import ReviewEngineState

logger = logging.getLogger(__name__)

# -- CONSTANTS ----------------------------------------------------------------

# Budget karakter per section (total target ~3500 chars untuk evidence)
SECTION_BUDGETS = {
    "abstract":     500,
    "introduction": 800,
    "method":       800,
    "results":      600,
    "conclusion":   500,
}

# Regex patterns untuk mendeteksi section headers
# pymupdf4llm menghasilkan format seperti:
#   ## **Abstract**
#   ## **1 Introduction**
#   ## I. INTRODUCTION
#   ## **3 Model Architecture**
#   ## **7 Conclusion**
# Key: header dimulai dengan # dan mungkin dibungkus **bold**
SECTION_PATTERNS = {
    "abstract": [
        r"(?:^|\n)\s*#{1,3}\s*\*{0,2}\s*abstract\s*\*{0,2}\s*(?:\n|$)",
        r"(?:^|\n)\s*\*{2}abstract\*{2}\s*(?:\n|$)",
        r"(?:^|\n)\s*abstract\s*(?:\n|$)",
    ],
    "introduction": [
        r"(?:^|\n)\s*#{1,3}\s*\*{0,2}\s*(?:\d+[\.)]?\s+|[IV]+[\.)\s]\s*)?introduction\s*\*{0,2}\s*(?:\n|$)",
        r"(?:^|\n)\s*\*{0,2}\s*(?:\d+[\.)]?\s+)?pendahuluan\s*\*{0,2}\s*(?:\n|$)",
    ],
    "method": [
        r"(?:^|\n)\s*#{1,3}\s*\*{0,2}\s*(?:\d+[\.)]?\s+)?(?:model\s+architecture|method(?:ology|s)?|approach|proposed\s+(?:method|approach|system|framework)|training)\s*\*{0,2}\s*(?:\n|$)",
        r"(?:^|\n)\s*#{1,3}\s*\*{0,2}\s*(?:\d+[\.)]?\s+)?(?:metode|metodologi)\s*\*{0,2}\s*(?:\n|$)",
    ],
    "results": [
        r"(?:^|\n)\s*#{1,3}\s*\*{0,2}\s*(?:\d+[\.)]?\s+)?(?:results?(?:\s+and\s+discussion)?|experiments?(?:\s+and\s+results?)?|evaluation)\s*\*{0,2}\s*(?:\n|$)",
        r"(?:^|\n)\s*#{1,3}\s*\*{0,2}\s*(?:\d+[\.)]?\s+)?(?:hasil(?:\s+dan\s+pembahasan)?)\s*\*{0,2}\s*(?:\n|$)",
    ],
    "conclusion": [
        r"(?:^|\n)\s*#{1,3}\s*\*{0,2}\s*(?:\d+[\.)]?\s+)?(?:conclusion(?:s)?(?:\s+and\s+future\s+work)?|summary)\s*\*{0,2}\s*(?:\n|$)",
        r"(?:^|\n)\s*#{1,3}\s*\*{0,2}\s*(?:\d+[\.)]?\s+)?(?:kesimpulan|simpulan)\s*\*{0,2}\s*(?:\n|$)",
    ],
}

# Pattern untuk mendeteksi header apapun (batas section berikutnya)
NEXT_SECTION_PATTERN = re.compile(
    r"\n\s*#{1,3}\s*\*{0,2}\s*(?:\d+[\.\)]?\s*)?[A-Z]",
    re.MULTILINE,
)

# -- HELPERS ------------------------------------------------------------------

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
        print(f"[evidence_select][log_step] log gagal (diabaikan): {exc}")


def _find_section(text: str, section_name: str) -> tuple[int, int] | None:
    """
    Cari posisi awal section di raw_markdown.
    Return (start, end) atau None jika tidak ditemukan.
    """
    patterns = SECTION_PATTERNS.get(section_name, [])

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            return match.start(), match.end()

    return None


def _extract_section_content(text: str, section_name: str, max_chars: int) -> str | None:
    """
    Extract konten dari sebuah section sampai section berikutnya.
    """
    pos = _find_section(text, section_name)
    if pos is None:
        return None

    start = pos[1]  # Mulai setelah header
    remaining = text[start:]

    # Cari awal section berikutnya (any markdown header)
    next_section = NEXT_SECTION_PATTERN.search(remaining)

    if next_section:
        content = remaining[:next_section.start()]
    else:
        content = remaining

    # Trim dan limit
    content = content.strip()
    if len(content) > max_chars:
        # Potong di batas kalimat terakhir yang muat
        truncated = content[:max_chars]
        last_period = truncated.rfind(".")
        if last_period > max_chars * 0.5:
            content = truncated[:last_period + 1]
        else:
            content = truncated + "..."

    return content if content else None


def _extract_evidence_chunks(raw_markdown: str) -> list[dict]:
    """
    Extract evidence chunks dari raw_markdown berdasarkan section detection.
    Return list of {"section": str, "content": str, "chars": int}.
    """
    chunks = []

    for section_name, budget in SECTION_BUDGETS.items():
        content = _extract_section_content(raw_markdown, section_name, budget)
        if content and len(content) > 50:  # Skip section terlalu pendek
            chunks.append({
                "section": section_name,
                "content": content,
                "chars": len(content),
            })

    return chunks


def _fallback_chunks(state: ReviewEngineState) -> list[dict]:
    """
    Fallback jika section detection gagal:
    head (2000) + middle (1000) + tail (1000) dari raw_markdown.
    """
    raw = state.get("raw_markdown") or ""
    if not raw:
        head = state.get("document_head") or ""
        tail = state.get("document_tail") or ""
        chunks = []
        if head:
            chunks.append({"section": "head", "content": head[:2000], "chars": min(len(head), 2000)})
        if tail:
            chunks.append({"section": "tail", "content": tail[:1000], "chars": min(len(tail), 1000)})
        return chunks

    total = len(raw)
    chunks = []

    # Head: first 2000 chars
    chunks.append({
        "section": "head",
        "content": raw[:2000].strip(),
        "chars": min(total, 2000),
    })

    # Middle: center 1000 chars
    if total > 4000:
        mid_start = total // 2 - 500
        chunks.append({
            "section": "middle",
            "content": raw[mid_start:mid_start + 1000].strip(),
            "chars": 1000,
        })

    # Tail: last 1000 chars
    if total > 2000:
        chunks.append({
            "section": "tail",
            "content": raw[-1000:].strip(),
            "chars": min(total, 1000),
        })

    return chunks


def _build_metadata_section(state: ReviewEngineState) -> str:
    """Bangun blok metadata ringkas."""
    title = state.get("title") or "Tidak tersedia"
    abstract = state.get("abstract") or ""
    authors = state.get("authors") or []
    keywords = state.get("keywords") or []
    domain = state.get("domain") or ""
    sub_domain = state.get("sub_domain") or ""
    paper_type = state.get("paper_type") or ""

    lines = ["PAPER METADATA", f"- Title: {title}"]

    if authors:
        lines.append(f"- Authors: {', '.join(authors[:5])}")
    if keywords:
        lines.append(f"- Keywords: {', '.join(keywords)}")
    if domain:
        lines.append(f"- Domain: {domain}/{sub_domain}" if sub_domain else f"- Domain: {domain}")
    if paper_type:
        lines.append(f"- Paper type: {paper_type}")
    if abstract:
        lines.append(f"\nABSTRACT\n{abstract[:800]}")

    return "\n".join(lines)


def _build_references_section(state: ReviewEngineState) -> str:
    """Bangun blok referensi dari top_references."""
    top_refs = state.get("top_references") or []
    if not top_refs:
        return ""

    lines = ["RELEVANT REFERENCES"]
    for i, ref in enumerate(top_refs[:5], 1):
        title = ref.get("title", "Untitled")
        year = ref.get("year", "N/A")
        authors = ref.get("authors", [])
        snippet = (ref.get("snippet") or "")[:150]
        author_str = ", ".join(authors[:3]) if authors else "Unknown"
        lines.append(f"[{i}] {title} ({author_str}, {year})\n    {snippet}")

    return "\n".join(lines)


# -- NODE UTAMA ---------------------------------------------------------------

async def evidence_select_node(state: ReviewEngineState) -> dict:
    """
    LangGraph node: Memilih evidence chunks dan merakit review_context.

    Input dari state:
        - raw_markdown (untuk section extraction)
        - document_head, document_tail (fallback)
        - title, abstract, authors, keywords, domain, paper_type (metadata)
        - top_references (dari search_rank)
        - analysis_id (untuk logging)

    Output (di-merge ke state):
        - evidence_chunks : list[dict] potongan per section
        - review_context  : str context final untuk LLM scoring
    """
    analysis_id = state.get("analysis_id", "unknown")
    raw_markdown = state.get("raw_markdown") or ""

    print(f"\n[evidence_select] Memulai seleksi evidence...")
    print(f"[evidence_select] raw_markdown: {len(raw_markdown)} chars")
    _safe_log(analysis_id, "evidence", "processing", "Menyiapkan evidence untuk review...")

    # --- Step 1: Extract evidence chunks ---
    chunks = _extract_evidence_chunks(raw_markdown) if raw_markdown else []

    # Fallback jika terlalu sedikit section terdeteksi
    if len(chunks) < 2:
        print(f"[evidence_select] Section detection: {len(chunks)} sections (insufficient), using fallback")
        chunks = _fallback_chunks(state)
        extraction_method = "fallback (head/middle/tail)"
    else:
        extraction_method = "section-based"
        print(f"[evidence_select] Section detection berhasil:")
        for c in chunks:
            print(f"  - {c['section']}: {c['chars']} chars")

    # --- Step 2: Rakit review_context ---
    metadata_section = _build_metadata_section(state)
    references_section = _build_references_section(state)

    # Evidence body
    evidence_lines = ["DOCUMENT EVIDENCE"]
    for c in chunks:
        section_label = c["section"].upper()
        evidence_lines.append(f"[{section_label}]\n{c['content']}")

    evidence_body = "\n\n".join(evidence_lines)

    # Assemble final review_context
    sections = [metadata_section, evidence_body]
    if references_section:
        sections.append(references_section)

    review_context = "\n\n".join(sections)

    # --- Logging ---
    context_len = len(review_context)
    chunks_count = len(chunks)
    refs_count = len(state.get("top_references") or [])
    total_evidence = sum(c["chars"] for c in chunks)

    print(f"[evidence_select] review_context: {context_len} chars")
    print(f"[evidence_select] Evidence: {chunks_count} chunks ({total_evidence} chars), method: {extraction_method}")
    print(f"[evidence_select] References: {refs_count}")

    _safe_log(
        analysis_id, "evidence", "done",
        f"Evidence siap: {context_len} chars ({chunks_count} chunks, {refs_count} refs)",
    )

    return {
        "evidence_chunks": chunks,
        "review_context": review_context,
    }
