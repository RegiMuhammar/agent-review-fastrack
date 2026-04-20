"""
bizplan_search_prep.py - Persiapan query Tavily untuk business plan
===================================================================
Membentuk query pencarian pasar dan kompetitor yang sempit, praktis,
dan relevan untuk validasi asumsi business plan.
"""

from __future__ import annotations

from app.graph.state import ReviewEngineState


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
        print(f"[bizplan_search_prep][log_step] log gagal (diabaikan): {exc}")


def _compact_list(values: list[str], limit: int) -> str:
    clean = [value.strip() for value in values if value and value.strip()]
    return ", ".join(clean[:limit])


async def bizplan_search_prep_node(state: ReviewEngineState) -> dict:
    """
    Bangun query Tavily untuk market validation jalur bizplan.

    Output:
    - search_queries hanya berisi key `tavily`
    """
    analysis_id = state.get("analysis_id", "unknown")
    title = state.get("title") or "business plan"
    company_name = state.get("company_name") or title
    industry = state.get("industry") or "industri terkait"
    geography = state.get("geography") or "Indonesia"
    target_customer = state.get("target_customer") or []
    revenue_model = state.get("revenue_model") or []
    pricing_signals = state.get("pricing_signals") or []

    print("\n[bizplan_search_prep] Menyusun query validasi pasar dan kompetitor...")
    _safe_log(analysis_id, "bizplan_query_gen", "processing", "Menyusun query Tavily untuk validasi business plan...")

    customer_phrase = _compact_list(target_customer, 2) or "pelanggan bisnis"
    revenue_phrase = _compact_list(revenue_model, 2) or "model pendapatan"
    pricing_phrase = pricing_signals[0] if pricing_signals else f"{industry} pricing benchmark {geography}"

    tavily_queries = [
        f"{industry} market size {geography}",
        f"{industry} competitors {geography} {customer_phrase}",
        f"{company_name} alternatives {industry} {geography}",
        f"{industry} pricing benchmark {geography} {revenue_phrase}",
        pricing_phrase,
    ]

    deduped_queries: list[str] = []
    seen: set[str] = set()
    for query in tavily_queries:
        normalized = query.strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped_queries.append(query.strip())

    search_queries = {"tavily": deduped_queries[:5]}

    print(f"[bizplan_search_prep] Query Tavily: {search_queries['tavily']}")
    _safe_log(
        analysis_id,
        "bizplan_query_gen",
        "done",
        f"Query Tavily siap: {len(search_queries['tavily'])} query",
    )

    return {"search_queries": search_queries}
