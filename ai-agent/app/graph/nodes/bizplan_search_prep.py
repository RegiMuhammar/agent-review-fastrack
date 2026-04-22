"""
bizplan_search_prep.py - Persiapan query Tavily untuk business plan
===================================================================
Membentuk query pencarian pasar dan kompetitor yang sempit, praktis,
dan relevan untuk validasi asumsi business plan.
"""

from __future__ import annotations

import re

from app.graph.state import ReviewEngineState

GENERIC_TOPIC_TERMS = {
    "business",
    "startup",
    "indonesia",
    "education technology",
    "technology",
    "software",
    "saas",
}


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


def _customer_anchor(target_customer: list[str], industry: str) -> str:
    joined = " ".join(target_customer).lower()
    for token in ["campus", "kampus", "university", "universitas", "school", "sekolah"]:
        if token in joined:
            return "campus software" if token in {"campus", "kampus", "university", "universitas"} else "school software"
    if industry.strip():
        return f"{industry} software"
    return "business software"


def _topic_phrase(keywords: list[str], company_name: str, industry: str, geography: str) -> str:
    blocked = {
        company_name.lower().strip(),
        industry.lower().strip(),
        geography.lower().strip(),
        "business",
        "startup",
        "indonesia",
    }
    candidates: list[str] = []
    for keyword in keywords:
        text = keyword.strip()
        if not text:
            continue
        lowered = text.lower()
        if lowered in blocked:
            continue
        if len(text) < 4:
            continue
        candidates.append(text.lower())
        if len(candidates) >= 2:
            break
    return " ".join(candidates)


def _topical_modifier(keywords: list[str], company_name: str, industry: str, geography: str) -> str:
    for keyword in keywords:
        text = re.sub(r"\s+", " ", (keyword or "").strip()).lower()
        if not text or text in GENERIC_TOPIC_TERMS:
            continue
        if text in {company_name.lower().strip(), industry.lower().strip(), geography.lower().strip()}:
            continue
        if len(text) < 5:
            continue
        if text == "circular economy":
            return "sustainability"
        return text
    return ""


def _category_anchor(customer_anchor: str, keywords: list[str], company_name: str, industry: str, geography: str) -> str:
    modifier = _topical_modifier(keywords, company_name, industry, geography)
    if not modifier:
        return customer_anchor
    if modifier in customer_anchor.lower():
        return customer_anchor
    if " software" in customer_anchor:
        return customer_anchor.replace(" software", f" {modifier} software")
    return f"{customer_anchor} {modifier}".strip()


def _vendor_directory_query(customer_anchor: str, competitor_anchor: str, geography: str) -> str:
    lowered_anchor = customer_anchor.lower()
    if "campus" in lowered_anchor:
        return f"top higher education software vendors {geography}".strip()
    if "school" in lowered_anchor:
        return f"top school management software vendors {geography}".strip()
    return f"top {competitor_anchor} vendor directory {geography}".strip()


def _extract_pricing_terms(signal: str) -> list[str]:
    lowered = signal.lower()
    terms: list[str] = []

    for needle, label in [
        ("subscription", "subscription"),
        ("langganan", "subscription"),
        ("paket", "subscription"),
        ("license", "license"),
        ("lisensi", "license"),
        ("setup fee", "setup fee"),
        ("komisi", "commission"),
        ("commission", "commission"),
        ("transaction fee", "transaction fee"),
        ("per tahun", "annual"),
        ("per bulan", "monthly"),
        ("campus", "campus"),
        ("kampus", "campus"),
        ("school", "school"),
        ("sekolah", "school"),
        ("university", "university"),
    ]:
        if needle in lowered and label not in terms:
            terms.append(label)

    return terms


def _select_pricing_query(pricing_signals: list[str], anchor: str, geography: str) -> str:
    for signal in pricing_signals:
        lowered = signal.lower()
        if any(token in lowered for token in ["pricing", "harga", "paket", "langganan", "subscription", "per bulan", "per tahun"]):
            terms = _extract_pricing_terms(signal)
            if terms:
                compact_terms = " ".join(term for term in terms[:4] if term not in {"subscription", "pricing benchmark"})
                suffix = f" {compact_terms}" if compact_terms else ""
                return f"{anchor} {geography}{suffix}".strip()
    return f"{anchor} {geography}".strip()


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
    keywords = state.get("keywords") or []

    print("\n[bizplan_search_prep] Menyusun query validasi pasar dan kompetitor...")
    _safe_log(analysis_id, "bizplan_query_gen", "processing", "Menyusun query Tavily untuk validasi business plan...")

    customer_phrase = _compact_list(target_customer, 2) or "pelanggan bisnis"
    revenue_phrase = _compact_list(revenue_model, 2) or "model pendapatan"
    customer_anchor = _customer_anchor(target_customer, industry)
    topic_phrase = _topic_phrase(keywords, company_name, industry, geography)
    market_anchor = " ".join(part for part in [customer_anchor, topic_phrase] if part).strip() or industry
    competitor_anchor = _category_anchor(customer_anchor, keywords, company_name, industry, geography)
    pricing_anchor = " ".join(part for part in [customer_anchor, "pricing benchmark"] if part).strip()
    pricing_phrase = _select_pricing_query(pricing_signals, pricing_anchor, geography)

    tavily_queries = [
        f"{market_anchor} market size {geography}".strip(),
        f"{competitor_anchor} competitors {geography}".strip(),
        f"best {competitor_anchor} providers {geography}".strip(),
        _vendor_directory_query(customer_anchor, competitor_anchor, geography),
        f"{customer_anchor} pricing benchmark {geography} {revenue_phrase}".strip(),
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
