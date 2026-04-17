from app.services.laravel_client import log_step

async def essay_agent_node(state: dict) -> dict:
    """Prepare context dan search queries untuk essay preview."""
    await log_step(state["analysis_id"], "preparing", "processing", "Menyiapkan analisis essay...")

    # Siapkan context dari dokumen
    agent_context = state["raw_markdown"][:6000]  # Batasi untuk context window

    # Generate search queries berdasarkan topik essay
    search_queries = {}  # MVP: essay belum pakai external search
    
    await log_step(state["analysis_id"], "preparing", "done", "Konteks analisis siap")
    
    return {
        "agent_context": agent_context,
        "search_queries": search_queries,
    }