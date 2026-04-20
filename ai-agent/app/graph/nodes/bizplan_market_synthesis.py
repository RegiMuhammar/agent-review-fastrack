"""
bizplan_market_synthesis.py - Sintesis validasi pasar business plan
===================================================================
Merangkum hasil pencarian Tavily menjadi sinyal pasar yang ringkas dan
aman untuk diteruskan ke `bizplan_agent` dan `generate`.
"""

from __future__ import annotations

import re

from app.graph.state import ReviewEngineState


COMPETITOR_HINTS = [
    "competitor",
    "competitors",
    "competition",
    "competitive",
    "rival",
    "alternatives",
    "alternative",
    "pesaing",
    "kompetitor",
    "kompetisi",
]

MARKET_HINTS = [
    "market",
    "pasar",
    "industry",
    "industri",
    "growth",
    "permintaan",
    "adoption",
    "adopsi",
    "benchmark",
    "pricing",
]


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
        print(f"[bizplan_market_synthesis][log_step] log gagal (diabaikan): {exc}")


def _clean_text(text: str, limit: int = 220) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "")).strip()
    return cleaned[:limit]


def _split_market_vs_competition(results: list[dict]) -> tuple[list[dict], list[dict]]:
    market_results: list[dict] = []
    competition_results: list[dict] = []

    for result in results:
        haystack = f"{result.get('title', '')} {result.get('snippet', '')}".lower()
        if any(hint in haystack for hint in COMPETITOR_HINTS):
            competition_results.append(result)
        if any(hint in haystack for hint in MARKET_HINTS):
            market_results.append(result)

    if not market_results:
        market_results = results[:3]
    if not competition_results:
        competition_results = results[:2]

    return market_results[:3], competition_results[:3]


def _summarize_results(results: list[dict]) -> str:
    if not results:
        return ""
    snippets = []
    for result in results[:3]:
        title = _clean_text(result.get("title", "Tanpa judul"), 90)
        snippet = _clean_text(result.get("snippet", ""), 140)
        snippets.append(f"{title}: {snippet}" if snippet else title)
    return " | ".join(snippets)


def _extract_competitor_names(results: list[dict]) -> list[str]:
    names: list[str] = []
    for result in results:
        title = _clean_text(result.get("title", ""), 90)
        if not title:
            continue
        names.append(title)
    deduped: list[str] = []
    seen: set[str] = set()
    for name in names:
        lowered = name.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        deduped.append(name)
    return deduped[:4]


async def bizplan_market_synthesis_node(state: ReviewEngineState) -> dict:
    """
    Sintesis hasil Tavily untuk business plan.

    Output:
    - external_market_evidence
    - competitive_evidence
    - market_validation_status
    - market_validation
    - competition_insights
    - market_red_flags
    """
    analysis_id = state.get("analysis_id", "unknown")
    top_references = state.get("top_references") or []
    ranked_results = state.get("ranked_results") or []
    company_name = state.get("company_name") or state.get("title") or "business plan ini"
    industry = state.get("industry") or "industri terkait"
    geography = state.get("geography") or "pasar target"

    print("\n[bizplan_market_synthesis] Menyintesis validasi pasar dari hasil pencarian...")
    _safe_log(analysis_id, "bizplan_market", "processing", "Menyintesis validasi pasar dan kompetitor...")

    source_results = top_references or ranked_results
    if not source_results:
        market_red_flags = [
            "Validasi pasar eksternal belum tersedia.",
            "Kompetitor eksternal belum dapat diverifikasi.",
        ]
        _safe_log(analysis_id, "bizplan_market", "done", "Validasi pasar selesai dengan status kosong.")
        return {
            "external_market_evidence": [],
            "competitive_evidence": [],
            "market_validation_status": "unavailable",
            "market_validation": {
                "status": "unavailable",
                "market_size_summary": "",
                "evidence": [],
            },
            "competition_insights": {
                "direct_competitors": [],
                "substitutes": [],
                "key_risk": "Belum ada bukti eksternal yang cukup untuk menilai kompetisi.",
            },
            "market_red_flags": market_red_flags,
        }

    market_results, competition_results = _split_market_vs_competition(source_results)
    market_summary = _summarize_results(market_results)
    competition_names = _extract_competitor_names(competition_results)

    market_validation_status = "validated" if len(source_results) >= 3 else "partial"
    market_red_flags: list[str] = []
    if len(source_results) < 2:
        market_red_flags.append("Bukti eksternal pasar masih sangat terbatas.")
    if not competition_names:
        market_red_flags.append("Kompetitor langsung belum teridentifikasi dengan jelas.")

    competition_risk = (
        f"Pasar {industry} di {geography} memiliki pemain pembanding yang perlu dianalisis lebih lanjut."
        if competition_names else
        f"Risiko kompetisi untuk {company_name} belum tervalidasi kuat dari sumber eksternal."
    )

    external_market_evidence = [
        {
            "title": item.get("title", "Tanpa judul"),
            "url": item.get("url", ""),
            "source": item.get("source", ""),
            "snippet": _clean_text(item.get("snippet", ""), 220),
        }
        for item in market_results
    ]
    competitive_evidence = [
        {
            "title": item.get("title", "Tanpa judul"),
            "url": item.get("url", ""),
            "source": item.get("source", ""),
            "snippet": _clean_text(item.get("snippet", ""), 220),
        }
        for item in competition_results
    ]

    market_validation = {
        "status": market_validation_status,
        "market_size_summary": market_summary,
        "evidence": external_market_evidence,
    }
    competition_insights = {
        "direct_competitors": competition_names,
        "substitutes": [],
        "key_risk": competition_risk,
    }

    print(
        f"[bizplan_market_synthesis] Status: {market_validation_status} | "
        f"market evidence: {len(external_market_evidence)} | competitor evidence: {len(competitive_evidence)}"
    )
    _safe_log(
        analysis_id,
        "bizplan_market",
        "done",
        f"Validasi pasar siap ({market_validation_status}, {len(source_results)} referensi)",
    )

    return {
        "external_market_evidence": external_market_evidence,
        "competitive_evidence": competitive_evidence,
        "market_validation_status": market_validation_status,
        "market_validation": market_validation,
        "competition_insights": competition_insights,
        "market_red_flags": market_red_flags,
    }
