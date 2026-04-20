"""
essay_agent.py — Node sintesis konteks untuk esai
Dipanggil setelah proses dokumentasi profil (jika tanpa search), 
atau setelah proses evidence_select (jika dengan web search).
Tugas utamanya adalah merakit `review_context` yang kaya bagi prompt skor.
"""

from app.graph.state import ReviewEngineState
from app.services.laravel_client import log_step


def _build_external_reference_block(top_references: list[dict]) -> str:
    """Ringkas referensi eksternal yang lolos ranking untuk fact-check essay."""
    if not top_references:
        return ""

    lines = ["REFERENSI EKSTERNAL TERPILIH:"]
    for idx, ref in enumerate(top_references[:5], 1):
        title = ref.get("title", "Untitled")
        source = ref.get("source", "unknown")
        year = ref.get("year", "N/A")
        snippet = (ref.get("snippet") or "").strip()[:220]
        lines.append(f"[{idx}] ({source}, {year}) {title}")
        if snippet:
            lines.append(f"    {snippet}")
    return "\n".join(lines)


async def essay_agent_node(state: ReviewEngineState) -> dict:
    """Merakit review_context akhir sebelum scoring berdasarkan ketersediaan evidence web."""
    analysis_id = state.get("analysis_id", "unknown")
    await log_step(analysis_id, "synthesis", "processing", "Menyusun konteks evaluasi akhir esai...")
    
    agent_context = state.get("agent_context", "")
    run_search = state.get("run_essay_web_search", False)
    top_references = state.get("top_references", [])
    
    # Kumpulkan evidence eksternal hanya dari hasil retrieval, bukan evidence_chunks internal dokumen.
    external_references = _build_external_reference_block(top_references) if run_search else ""

    if not run_search:
        external_status = "(Pencarian eksternal tidak dijalankan; evaluasi fokus pada kualitas argumen internal essay.)"
    elif external_references:
        external_status = "(Pencarian eksternal dijalankan; referensi di bawah dapat dipakai untuk verifikasi klaim faktual.)"
    else:
        external_status = "(Pencarian eksternal dijalankan, tetapi tidak ada referensi yang lolos ranking untuk verifikasi kuat.)"

    review_context = f"""=== TEKS ESAI UTAMA ===
{agent_context}

=== STATUS VERIFIKASI EKSTERNAL ===
{external_status}

{external_references}
"""
    
    await log_step(analysis_id, "synthesis", "done", "Konteks telah disintesis.")
    
    return {
        "review_context": review_context
    }
