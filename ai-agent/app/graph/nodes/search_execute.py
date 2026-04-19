"""
search_execute.py — Search Executor Node (Fase 5)
===================================================
Menjalankan search queries dari retrieval_prep ke tiga sumber:
- Semantic Scholar (gratis, REST API)
- arXiv (gratis, arxiv package)
- Tavily (butuh API key)

Semua search dijalankan secara concurrent (asyncio + ThreadPool).
Hasil di-dedup berdasarkan normalized title.
Pipeline tetap jalan meskipun semua search gagal.

Flow: ... → retrieval_prep → search_execute → research_agent → ...
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from app.graph.state import ReviewEngineState
from app.tools.search_tools import (
    search_tavily,
    search_arxiv,
    search_semanticscholar,
    dedup_results,
)

logger = logging.getLogger(__name__)

# ThreadPool untuk menjalankan sync search functions secara concurrent
_executor = ThreadPoolExecutor(max_workers=3)

# Limit hasil per source per query
MAX_RESULTS_PER_QUERY = 3


# ── HELPERS ──────────────────────────────────────────────────────────────────

def _safe_log(analysis_id: str, step: str, status: str, message: str) -> None:
    """Logging ke Laravel secara best-effort."""
    try:
        import asyncio as _aio
        from app.services.laravel_client import log_step
        try:
            loop = _aio.get_running_loop()
            loop.create_task(log_step(analysis_id, step, status, message))
        except RuntimeError:
            _aio.run(log_step(analysis_id, step, status, message))
    except Exception as exc:
        print(f"[search_execute][log_step] log gagal (diabaikan): {exc}")


# ── NODE UTAMA ───────────────────────────────────────────────────────────────

async def search_execute_node(state: ReviewEngineState) -> dict:
    """
    LangGraph node: Jalankan search queries ke semua sources secara concurrent.

    Input dari state:
        - search_queries : dict per source dari retrieval_prep
        - analysis_id    : untuk logging

    Output (di-merge ke state):
        - search_results : list[dict] hasil search terdedup
    """
    analysis_id = state.get("analysis_id", "unknown")
    search_queries = state.get("search_queries") or {}

    print(f"\n[search_execute] Memulai pencarian eksternal...")
    _safe_log(analysis_id, "searching", "processing", "Mencari referensi dari sumber eksternal...")

    # ─── Guard: jika tidak ada queries ────────────────────────────────────
    if not search_queries or all(len(v) == 0 for v in search_queries.values()):
        print("[search_execute] WARNING: tidak ada search queries, skip")
        _safe_log(analysis_id, "searching", "done", "Search: skip (tidak ada queries)")
        return {"search_results": []}

    # ─── Ambil queries per source ─────────────────────────────────────────
    scholar_queries = search_queries.get("semanticscholar", [])
    arxiv_queries = search_queries.get("arxiv", [])
    tavily_queries = search_queries.get("tavily", [])

    # ─── Jalankan secara concurrent ───────────────────────────────────────
    loop = asyncio.get_event_loop()
    tasks = []

    if scholar_queries:
        tasks.append(("semanticscholar", loop.run_in_executor(
            _executor, search_semanticscholar, scholar_queries, MAX_RESULTS_PER_QUERY
        )))
    if arxiv_queries:
        tasks.append(("arxiv", loop.run_in_executor(
            _executor, search_arxiv, arxiv_queries, MAX_RESULTS_PER_QUERY
        )))
    if tavily_queries:
        tasks.append(("tavily", loop.run_in_executor(
            _executor, search_tavily, tavily_queries, MAX_RESULTS_PER_QUERY
        )))

    all_results: list[dict] = []
    source_counts = {"semanticscholar": 0, "arxiv": 0, "tavily": 0}

    for source_name, task in tasks:
        try:
            results = await task
            if isinstance(results, list):
                all_results.extend(results)
                source_counts[source_name] = len(results)
                print(f"[search_execute] {source_name}: {len(results)} results")
        except Exception as e:
            print(f"[search_execute] WARNING: {source_name} gagal: {e}")
            logger.warning(f"Search {source_name} failed: {e}")

    # ─── Dedup ────────────────────────────────────────────────────────────
    deduped = dedup_results(all_results)

    total = len(deduped)
    summary = (
        f"Search selesai — {total} hasil "
        f"(SS:{source_counts['semanticscholar']}, "
        f"arXiv:{source_counts['arxiv']}, "
        f"Tavily:{source_counts['tavily']})"
    )
    print(f"[search_execute] {summary}")
    _safe_log(analysis_id, "searching", "done", summary)

    return {"search_results": deduped}
