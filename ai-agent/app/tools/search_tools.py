"""
search_tools.py — Search Functions per Source (Fase 5)
=======================================================
Tiga fungsi search independen:
- Tavily: web search via API (butuh TAVILY_API_KEY)
- arXiv: gratis, via package `arxiv`
- Semantic Scholar: gratis, via REST API (httpx)

Semua fungsi mengembalikan list[dict] dengan format konsisten:
{
    "source": str,
    "title": str,
    "url": str,
    "snippet": str,
    "relevance_score": float,
    "year": int | None,
    "authors": list[str],
}
"""

import logging
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


# ── TAVILY ───────────────────────────────────────────────────────────────────

def search_tavily(queries: list[str], max_results_per_query: int = 3) -> list[dict]:
    """
    Search via Tavily API.
    Butuh TAVILY_API_KEY di .env.
    """
    from tavily import TavilyClient

    if not settings.TAVILY_API_KEY:
        logger.warning("TAVILY_API_KEY tidak diset, skip Tavily search")
        return []

    client = TavilyClient(api_key=settings.TAVILY_API_KEY)
    results: list[dict] = []
    seen_urls: set[str] = set()

    for query in queries:
        try:
            logger.info(f"Tavily search: '{query}'")
            response = client.search(
                query=query,
                search_depth="basic",      # "basic" lebih cepat & murah
                max_results=max_results_per_query,
                include_answer=False,
            )
            for item in response.get("results", []):
                url = item.get("url", "")
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                results.append({
                    "source": "tavily",
                    "title": item.get("title", "Untitled"),
                    "url": url,
                    "snippet": (item.get("content") or "")[:500],
                    "relevance_score": float(item.get("score", 0.5)),
                    "year": None,
                    "authors": [],
                })
        except Exception as e:
            logger.warning(f"Tavily search error for '{query}': {e}")

    logger.info(f"Tavily: {len(results)} results")
    return results


# ── ARXIV ────────────────────────────────────────────────────────────────────

def search_arxiv(queries: list[str], max_results_per_query: int = 3) -> list[dict]:
    """
    Search via arXiv API (gratis, tanpa API key).
    """
    try:
        import arxiv
    except ImportError:
        logger.warning("Package 'arxiv' tidak terinstall, skip arXiv search")
        return []

    client = arxiv.Client(num_retries=2, delay_seconds=1.0)
    results: list[dict] = []
    seen_ids: set[str] = set()

    for query in queries:
        try:
            logger.info(f"arXiv search: '{query}'")
            search = arxiv.Search(
                query=query,
                max_results=max_results_per_query,
                sort_by=arxiv.SortCriterion.Relevance,
            )
            for paper in client.results(search):
                arxiv_id = paper.entry_id.split("/abs/")[-1]
                if arxiv_id in seen_ids:
                    continue
                seen_ids.add(arxiv_id)

                year = paper.published.year if paper.published else None
                authors = [a.name for a in paper.authors[:4]]

                results.append({
                    "source": "arxiv",
                    "title": paper.title or "Untitled",
                    "url": paper.pdf_url or paper.entry_id,
                    "snippet": (paper.summary or "")[:500],
                    "relevance_score": 0.5,  # arXiv tidak return relevance score
                    "year": year,
                    "authors": authors,
                })
        except Exception as e:
            logger.warning(f"arXiv search error for '{query}': {e}")

    logger.info(f"arXiv: {len(results)} results")
    return results


# ── SEMANTIC SCHOLAR ─────────────────────────────────────────────────────────

S2_API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
S2_FIELDS = "title,abstract,year,authors,externalIds,url"

def search_semanticscholar(queries: list[str], max_results_per_query: int = 3) -> list[dict]:
    """
    Search via Semantic Scholar REST API (gratis, tanpa API key).
    Rate limit: ~100 req/5 min untuk unauthenticated.
    """
    results: list[dict] = []
    seen_ids: set[str] = set()

    for query in queries:
        try:
            logger.info(f"SemanticScholar search: '{query}'")
            resp = httpx.get(
                S2_API_URL,
                params={
                    "query": query,
                    "limit": max_results_per_query,
                    "fields": S2_FIELDS,
                },
                timeout=15,
            )

            if resp.status_code == 429:
                logger.warning("SemanticScholar rate limited, skip remaining queries")
                break

            resp.raise_for_status()
            data = resp.json()

            for paper in data.get("data", []):
                paper_id = paper.get("paperId", "")
                if paper_id in seen_ids:
                    continue
                seen_ids.add(paper_id)

                # Authors
                authors_raw = paper.get("authors") or []
                authors = [a.get("name", "") for a in authors_raw[:4] if isinstance(a, dict)]

                # URL
                url = paper.get("url") or f"https://www.semanticscholar.org/paper/{paper_id}"

                results.append({
                    "source": "semanticscholar",
                    "title": paper.get("title") or "Untitled",
                    "url": url,
                    "snippet": (paper.get("abstract") or "")[:500],
                    "relevance_score": 0.5,  # akan diranking di Fase 6
                    "year": paper.get("year"),
                    "authors": authors,
                })
        except httpx.HTTPStatusError as e:
            logger.warning(f"SemanticScholar HTTP error for '{query}': {e}")
        except Exception as e:
            logger.warning(f"SemanticScholar search error for '{query}': {e}")

    logger.info(f"SemanticScholar: {len(results)} results")
    return results


# ── DEDUP ────────────────────────────────────────────────────────────────────

def dedup_results(results: list[dict]) -> list[dict]:
    """
    Deduplikasi sederhana berdasarkan normalized title.
    Preferensi: pertahankan hasil yang muncul pertama.
    """
    seen_titles: set[str] = set()
    deduped: list[dict] = []

    for r in results:
        normalized = (r.get("title") or "").strip().lower()
        # Skip jika title kosong atau sudah ada
        if not normalized or normalized in seen_titles:
            continue
        seen_titles.add(normalized)
        deduped.append(r)

    removed = len(results) - len(deduped)
    if removed > 0:
        logger.info(f"Dedup: removed {removed} duplicates, {len(deduped)} remaining")

    return deduped
