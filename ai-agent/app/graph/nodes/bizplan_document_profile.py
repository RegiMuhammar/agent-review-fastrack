"""
bizplan_document_profile.py — Bizplan Document Profile Node
===========================================================
Node routing & profiling khusus jalur bizplan (Business Plan).
Berbeda dengan esai standar, node ini lebih fokus pada persiapan
struktur context khusus untuk business plan agar prompt engineering di tahap scoring lebih akurat.

Output: agent_context yang terstruktur memuat keseluruhan dokumen draft rancangan bisnis.
"""

from app.services.laravel_client import log_step
from app.graph.state import ReviewEngineState

async def bizplan_document_profile_node(state: ReviewEngineState) -> dict:
    """Prepare context dan (jika MVP nantinya ditambah) external search queries untuk bizplan."""
    analysis_id = state.get("analysis_id", "unknown")
    
    print(f"\n[bizplan_document_profile] Memulai persiapan context business plan...")
    await log_step(analysis_id, "preparing", "processing", "Menyiapkan analisis rancangan bisnis (Business Plan)...")

    title = state.get("title") or "Business Plan"
    raw_markdown = state.get("raw_markdown") or ""
    
    # Bizplan context builder
    # Untuk plan bisnis, kita beri instruksi implisit ke LLM dengan pembatas terstruktur
    context_builder = [
        "===========================================================",
        f" DOKUMEN BUSINESS PLAN: {title}",
        "===========================================================",
        "",
        "Dokumen berikut adalah narasi business plan. Mohon perhatikan:",
        "- Problem & Solution Statement",
        "- Market Analysis & Size",
        "- Business Model & Revenue Streams",
        "- Competitive Advantage",
        "- Tim dan Proyeksi Finansial",
        "",
        "--- START OF DOCUMENT ---",
        raw_markdown[:8000],  # Ambil porsi cukup besar dari awal
        "--- END OF DOCUMENT ---"
    ]
    
    agent_context = "\n".join(context_builder)
    
    search_queries = {}  # MVP: bizplan blm pakai external search API
    
    print(f"[bizplan_document_profile] Konteks disiapkan: {len(agent_context)} karakter.")
    await log_step(analysis_id, "preparing", "done", "Konteks Business Plan siap")
    
    return {
        "agent_context": agent_context,
        "search_queries": search_queries,
    }
