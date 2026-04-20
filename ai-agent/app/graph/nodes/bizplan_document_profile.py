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
    """Siapkan konteks awal dan placeholder search query untuk jalur bizplan."""
    analysis_id = state.get("analysis_id", "unknown")

    print("\n[bizplan_document_profile] Memulai persiapan konteks business plan...")
    await log_step(analysis_id, "preparing", "processing", "Menyiapkan konteks awal business plan...")

    title = state.get("title") or "Business Plan"
    raw_markdown = state.get("raw_markdown") or ""
    company_name = state.get("company_name") or title
    industry = state.get("industry") or "Tidak diketahui"
    geography = state.get("geography") or "Tidak diketahui"
    business_stage = state.get("business_stage") or "Tidak diketahui"
    target_customer = state.get("target_customer") or []
    funding_ask = state.get("funding_ask") or "Tidak disebutkan"
    revenue_model = state.get("revenue_model") or []

    context_builder = [
        "===========================================================",
        f" DOKUMEN RENCANA BISNIS: {title}",
        "===========================================================",
        "",
        "Snapshot awal business plan:",
        f"- Nama usaha/perusahaan: {company_name}",
        f"- Industri: {industry}",
        f"- Geografi: {geography}",
        f"- Tahap bisnis: {business_stage}",
        f"- Pendanaan yang dicari: {funding_ask}",
        f"- Target pelanggan: {', '.join(target_customer) if target_customer else 'Belum jelas'}",
        f"- Model pendapatan awal: {', '.join(revenue_model) if revenue_model else 'Belum jelas'}",
        "",
        "Dokumen berikut adalah narasi business plan. Mohon perhatikan:",
        "- Rumusan masalah dan solusi",
        "- Analisis pasar dan ukuran peluang",
        "- Model bisnis dan sumber pendapatan",
        "- Keunggulan kompetitif",
        "- Tim, eksekusi, dan proyeksi finansial",
        "",
        "--- AWAL DOKUMEN ---",
        raw_markdown[:8000],
        "--- AKHIR DOKUMEN ---",
    ]

    agent_context = "\n".join(context_builder)
    search_queries = {}

    print(f"[bizplan_document_profile] Konteks disiapkan: {len(agent_context)} karakter.")
    await log_step(analysis_id, "preparing", "done", "Konteks awal business plan siap.")

    return {
        "agent_context": agent_context,
        "search_queries": search_queries,
    }
