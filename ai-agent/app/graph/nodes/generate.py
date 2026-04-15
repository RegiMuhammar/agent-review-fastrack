from app.graph.state import ReviewEngineState

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

async def generate_node(state: ReviewEngineState) -> dict:
    """Node akhir: Generate Report format hasil evaluasi ke dalam struktur JSON."""
    analysis_id = state.get("analysis_id")

    print("\n[generate_node] Menyusun susunan akhir laporan...")
    _safe_log(analysis_id, "generating", "processing", "Menyusun kumpulan evaluasi ke laporan akhir...")

    # Kumpulkan dari State ReviewEngineState Langgraph
    final_result = {
        "analysis_id": analysis_id,
        "doc_type": state.get("doc_type"),
        "title": state.get("title") or "Dokumen Tanpa Judul",
        "page_count": state.get("page_count", 0),
        "score_overall": state.get("score_overall", 0.0),
        "summary": state.get("summary", ""),
        "dimensions": state.get("dimensions_feedback", []),
        "overall_feedback": state.get("overall_feedback", ""),
        # Array placeholder, idealnya LLM mengembalikan nilai ini juga di prompt fase 3
        # Untuk MVP fase 2, kita kosongi dulu, atau boleh disesuaikan dari prompt.
        "strengths": [],
        "improvements": [],
        "references": [], 
    }

    _safe_log(analysis_id, "generating", "done", "Laporan evaluasi berhasil disusun.")
    print("[generate_node] Selesai menyusun laporan akhir.\n")

    return {"final_result": final_result}