"""
essay_agent.py — Node sintesis konteks untuk esai
Dipanggil setelah proses dokumentasi profil (jika tanpa search), 
atau setelah proses evidence_select (jika dengan web search).
Tugas utamanya adalah merakit `review_context` yang kaya bagi prompt skor.
"""

from app.graph.state import ReviewEngineState
from app.services.laravel_client import log_step

async def essay_agent_node(state: ReviewEngineState) -> dict:
    """Merakit review_context akhir sebelum scoring berdasarkan ketersediaan evidence web."""
    analysis_id = state.get("analysis_id", "unknown")
    await log_step(analysis_id, "synthesis", "processing", "Menyusun konteks evaluasi akhir esai...")
    
    agent_context = state.get("agent_context", "")
    run_search = state.get("run_essay_web_search", False)
    
    # Kumpulkan evidence web jika pencarian dijalankan
    web_evidence = ""
    if run_search:
        # Prioritas 1: Ambil dari evidence chunks (jika ada)
        chunks = state.get("evidence_chunks", [])
        if chunks:
            web_evidence = "BUKTI FAKTUAL DARI PENCARIAN WEB:\n"
            for c in chunks:
                web_evidence += f"- {c.get('content', '')}\n"
        else:
            # Prioritas 2: Ambil dari top references
            refs = state.get("top_references", [])
            if refs:
                web_evidence = "REFERENSI WEB:\n"
                for r in refs:
                    web_evidence += f"- [{r.get('title', 'No Title')}] {r.get('snippet', '')}\n"

    # Jika pencarian tidak dijalankan atau tidak menemukan apa-apa
    if not web_evidence:
        web_info_status = "(Pencarian web eksternal tidak digunakan, evaluasi murni internal essay)."
    else:
        web_info_status = "(Dilengkapi dengan pengecekan fakta web)."

    # Rakit ulasan akhir
    review_context = f"""=== TEKS ESAI UTAMA ===
{agent_context}

=== STATUS & BUKTI EKSTERNAL ===
{web_info_status}

{web_evidence}
"""
    
    await log_step(analysis_id, "synthesis", "done", "Konteks telah disintesis.")
    
    return {
        "review_context": review_context
    }
