"""
bizplan_market_synthesis.py - Sintesis validasi pasar business plan
===================================================================
Merangkum hasil pencarian Tavily menjadi sinyal pasar yang ringkas dan
aman untuk diteruskan ke `bizplan_agent` dan `generate`.
"""

from __future__ import annotations

from difflib import SequenceMatcher
import re
from urllib.parse import urlparse

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

NON_COMPETITOR_TITLE_HINTS = [
    "market",
    "report",
    "study",
    "benchmark",
    "industry",
    "growth",
    "pricing",
    "research",
]

SUBSTITUTE_TITLE_HINTS = [
    "software",
    "platform",
    "system",
    "management",
    "dashboard",
    "cloud",
    "erp",
    "student information",
]

SOFTWARE_MARKET_HINTS = [
    "software",
    "platform",
    "dashboard",
    "erp",
    "app",
    "saas",
]

COMPETITOR_DISCOVERY_HINTS = [
    "top ",
    "best ",
    "leading ",
    "alternatives to",
    "alternative to",
    "vs ",
    "compare",
    "comparison",
    "vendor",
    "provider",
]

COMPETITION_FALSE_POSITIVE_HINTS = [
    "competitive landscape",
    "market overview",
    "market segmentation",
]

GENERIC_DIRECTORY_HINTS = [
    "companies in",
    "company in",
    "it companies",
    "agencies",
    "services",
]

NON_PRODUCT_SUBSTITUTE_HINTS = [
    "consulting",
    "consultancy",
    "consultant",
    "csr",
    "packaging",
    "commodity",
    "supply chain",
    "advisory",
]

COMPANY_ENTITY_STOPWORDS = {
    "discover",
    "there",
    "featured",
    "explore",
    "companies",
    "services",
    "top",
    "best",
    "leading",
    "this",
    "comparison",
    "start",
    "book",
    "request",
    "free",
    "trial",
    "indonesia",
    "college",
    "software",
    "platform",
    "system",
    "systems",
    "management",
    "solutions",
    "solution",
    "pricing",
    "report",
    "study",
    "market",
    "university",
    "universities",
    "campus",
    "education",
    "cloud",
}

BIZPLAN_RELEVANCE_THRESHOLD = 0.45
MARKET_FIT_THRESHOLD = 0.08
INDUSTRY_MARKET_HINTS = {
    "Pendidikan": ["education", "edtech", "school", "campus", "university", "student", "learning"],
    "SaaS": ["saas", "software", "platform", "dashboard", "subscription"],
    "Logistik": ["logistics", "logistic", "delivery", "fleet", "warehouse", "freight", "supply chain"],
    "Fintech": ["fintech", "payment", "lending", "wallet", "banking"],
    "Kesehatan": ["health", "healthtech", "medical", "clinic", "hospital"],
    "Pertanian": ["agri", "agritech", "farm", "farming", "crop", "agriculture"],
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
        print(f"[bizplan_market_synthesis][log_step] log gagal (diabaikan): {exc}")


def _clean_text(text: str, limit: int = 220) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "")).strip()
    return cleaned[:limit]


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def _has_similar_token(needle: str, haystack: str, threshold: float = 0.78) -> bool:
    needle_tokens = [token for token in _tokenize(needle) if len(token) >= 4]
    haystack_tokens = [token for token in _tokenize(haystack) if len(token) >= 4]
    for source in needle_tokens[:4]:
        for target in haystack_tokens[:24]:
            if source == target:
                return True
            if SequenceMatcher(None, source, target).ratio() >= threshold:
                return True
    return False


def _relevance_score(result: dict, company_name: str, industry: str, geography: str, target_customer: list[str]) -> int:
    haystack = f"{result.get('title', '')} {result.get('snippet', '')}".lower()
    score = 0
    if industry and (industry.lower() in haystack or _has_similar_token(industry, haystack)):
        score += 2
    if geography and geography.lower() in haystack:
        score += 1
    if company_name and company_name.lower() in haystack:
        score += 2
    for customer in target_customer[:3]:
        if customer and (customer.lower() in haystack or _has_similar_token(customer, haystack)):
            score += 1
    if any(hint in haystack for hint in COMPETITOR_HINTS + MARKET_HINTS):
        score += 1
    return score


def _market_fit_score(result: dict, industry: str, target_customer: list[str]) -> float:
    haystack = f"{result.get('title', '')} {result.get('snippet', '')}".lower()
    score = 0.0
    for customer in target_customer[:3]:
        if customer and (customer.lower() in haystack or _has_similar_token(customer, haystack)):
            score += 0.08
    industry_hints = INDUSTRY_MARKET_HINTS.get(industry, [])
    if any(hint in haystack for hint in industry_hints):
        score += 0.08
    if any(hint in haystack for hint in SOFTWARE_MARKET_HINTS):
        score += 0.08
    return round(min(score, 0.32), 3)


def _split_market_vs_competition(results: list[dict]) -> tuple[list[dict], list[dict]]:
    market_results: list[dict] = []
    competition_results: list[dict] = []

    for result in results:
        role = result.get("reference_role")
        if role == "competition":
            competition_results.append(result)
        if role in {"market", "pricing"}:
            market_results.append(result)

        haystack = f"{result.get('title', '')} {result.get('snippet', '')}".lower()
        if any(hint in haystack for hint in COMPETITOR_HINTS):
            competition_results.append(result)
        if any(hint in haystack for hint in MARKET_HINTS):
            market_results.append(result)

    if not market_results:
        market_results = results[:3]

    deduped_market: list[dict] = []
    deduped_competition: list[dict] = []
    seen_market: set[str] = set()
    seen_competition: set[str] = set()

    for result in market_results:
        key = (result.get("url") or result.get("title") or "").lower()
        if not key or key in seen_market:
            continue
        seen_market.add(key)
        deduped_market.append(result)

    for result in competition_results:
        key = (result.get("url") or result.get("title") or "").lower()
        if not key or key in seen_competition:
            continue
        seen_competition.add(key)
        deduped_competition.append(result)

    return deduped_market[:3], deduped_competition[:3]


def _infer_reference_role(result: dict) -> str:
    role = result.get("reference_role")
    if role:
        return str(role)
    haystack = f"{result.get('title', '')} {result.get('snippet', '')}".lower()
    if any(hint in haystack for hint in COMPETITOR_HINTS):
        return "competition"
    if "pricing" in haystack or "benchmark" in haystack:
        return "pricing"
    if any(hint in haystack for hint in MARKET_HINTS):
        return "market"
    return "general"


def _select_market_evidence(results: list[dict], industry: str, target_customer: list[str]) -> list[dict]:
    selected: list[dict] = []
    for result in results:
        role = _infer_reference_role(result)
        fit = result.get("market_fit_score")
        if fit is None:
            fit = _market_fit_score(result, industry, target_customer)
        if role == "pricing":
            selected.append(result)
            continue
        if role == "market" and float(fit) >= MARKET_FIT_THRESHOLD:
            selected.append(result)
    return selected[:3]


def _summarize_results(results: list[dict]) -> str:
    if not results:
        return ""
    snippets = []
    for result in results[:3]:
        title = _clean_text(result.get("title", "Tanpa judul"), 90)
        snippet = _clean_text(result.get("snippet", ""), 140)
        snippets.append(f"{title}: {snippet}" if snippet else title)
    return " | ".join(snippets)


def _is_generic_competitor_page(title: str) -> bool:
    lowered = title.lower()
    if any(hint in lowered for hint in NON_COMPETITOR_TITLE_HINTS):
        return True
    if any(hint in lowered for hint in GENERIC_DIRECTORY_HINTS):
        return True
    if any(hint in lowered for hint in COMPETITOR_DISCOVERY_HINTS) and any(hint in lowered for hint in SUBSTITUTE_TITLE_HINTS):
        return True
    return False


def _extract_brand_names(text: str, company_name: str) -> list[str]:
    matches = re.findall(
        r"\b(?:[A-Z][a-z0-9]+[A-Z][A-Za-z0-9]+|[A-Z][A-Za-z0-9&.-]{2,}(?:\s+[A-Z][A-Za-z0-9&.-]{2,}){0,2})\b",
        text or "",
    )
    candidates: list[str] = []
    company_lower = (company_name or "").lower().strip()
    for match in matches:
        cleaned = re.sub(r"\s+", " ", match).strip(" ,.;:-")
        lowered = cleaned.lower()
        if not cleaned or len(cleaned) < 4:
            continue
        if lowered == company_lower:
            continue
        tokens = [token.lower() for token in cleaned.split()]
        if not tokens:
            continue
        if tokens[0] in {"start", "book", "request", "get", "try", "watch"}:
            continue
        if tokens[0] in COMPANY_ENTITY_STOPWORDS:
            continue
        if all(token in COMPANY_ENTITY_STOPWORDS for token in tokens):
            continue
        generic_token_count = sum(1 for token in tokens if token in COMPANY_ENTITY_STOPWORDS)
        if generic_token_count >= max(1, len(tokens) - 1):
            continue
        if any(token in {"pdf", "indonesia"} for token in tokens) and len(tokens) == 1:
            continue
        candidates.append(cleaned)
    deduped: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        lowered = candidate.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        deduped.append(candidate)
    return deduped[:5]


def _extract_domain_brand(url: str) -> str:
    domain = urlparse(url or "").netloc.lower().replace("www.", "")
    label = domain.split(".")[0].replace("-", " ").strip()
    if not label:
        return ""
    tokens = [token.lower() for token in label.split()]
    if tokens[0] in {"example", "localhost"}:
        return ""
    if not tokens or all(token in COMPANY_ENTITY_STOPWORDS for token in tokens):
        return ""
    return label.title()


def _extract_competitor_names(results: list[dict], company_name: str) -> list[str]:
    names: list[str] = []
    for result in results:
        title = _clean_text(result.get("title", ""), 90)
        snippet = _clean_text(result.get("snippet", ""), 220)
        if not title:
            continue
        lowered = title.lower()
        haystack = f"{title} {snippet}".lower()
        explicit_competition = result.get("reference_role") == "competition" or any(hint in haystack for hint in COMPETITOR_HINTS)
        if not explicit_competition:
            continue
        if any(hint in haystack for hint in COMPETITION_FALSE_POSITIVE_HINTS):
            continue
        if not any(hint in haystack for hint in COMPETITOR_DISCOVERY_HINTS + SUBSTITUTE_TITLE_HINTS + ["software", "platform", "vendor", "provider", "tool"]):
            continue
        entity_source = snippet if _is_generic_competitor_page(title) else f"{title}. {snippet}"
        has_generic_product_title = any(hint in lowered for hint in SUBSTITUTE_TITLE_HINTS)
        has_generic_directory_title = any(hint in lowered for hint in GENERIC_DIRECTORY_HINTS)
        domain_brand = _extract_domain_brand(result.get("url", ""))
        brand_names = _extract_brand_names(entity_source, company_name)
        if domain_brand and not has_generic_directory_title:
            matching_brand = next((item for item in brand_names if item.lower() == domain_brand.lower()), "")
            if has_generic_product_title and matching_brand:
                brand_names = [matching_brand]
            elif has_generic_product_title:
                brand_names = [domain_brand] + brand_names
            elif domain_brand not in brand_names:
                brand_names.insert(0, domain_brand)
        if not _is_generic_competitor_page(title) and not (has_generic_product_title and brand_names):
            names.append(title)
        for candidate in brand_names:
            names.append(candidate)
    deduped: list[str] = []
    seen: set[str] = set()
    for name in names:
        lowered = name.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        deduped.append(name)
    return deduped[:4]


def _extract_substitute_names(results: list[dict]) -> list[str]:
    names: list[str] = []
    for result in results:
        title = _clean_text(result.get("title", ""), 90)
        if not title:
            continue
        lowered = title.lower()
        snippet = _clean_text(result.get("snippet", ""), 220).lower()
        haystack = f"{lowered} {snippet}"
        if any(hint in lowered for hint in NON_COMPETITOR_TITLE_HINTS if hint != "pricing"):
            continue
        if result.get("reference_role") == "competition":
            continue
        if any(hint in haystack for hint in NON_PRODUCT_SUBSTITUTE_HINTS):
            continue
        if result.get("reference_role") == "pricing":
            domain_brand = _extract_domain_brand(result.get("url", ""))
            if domain_brand:
                names.append(domain_brand)
                continue
        if any(hint in lowered for hint in SUBSTITUTE_TITLE_HINTS):
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
    target_customer = state.get("target_customer") or []

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

    relevant_results = [
        result for result in source_results
        if (
            result.get("relevance_score", 0.0) >= BIZPLAN_RELEVANCE_THRESHOLD
            or _relevance_score(result, company_name, industry, geography, target_customer) >= 2
        )
    ]
    candidate_results = relevant_results or source_results

    market_results, competition_results = _split_market_vs_competition(candidate_results)
    selected_market_results = _select_market_evidence(market_results, industry, target_customer)
    market_summary = _summarize_results(selected_market_results)
    competition_names = _extract_competitor_names(competition_results, company_name)
    substitute_names = _extract_substitute_names(relevant_results or candidate_results)

    role_market_results = [
        result for result in relevant_results
        if (
            result.get("reference_role") == "pricing"
            or (result.get("reference_role") == "market" and float(result.get("market_fit_score", 0.0)) >= MARKET_FIT_THRESHOLD)
        )
    ]
    role_competition_results = [result for result in relevant_results if result.get("reference_role") == "competition"]

    has_market_coverage = len(role_market_results) >= 2 or len(selected_market_results) >= 2
    has_competition_coverage = (len(role_competition_results) >= 1 or len(competition_results) >= 1) and len(competition_names) >= 1
    market_validation_status = (
        "validated"
        if len(relevant_results) >= 3 and has_market_coverage and has_competition_coverage
        else "partial"
    )
    market_red_flags: list[str] = []
    if len(source_results) < 2:
        market_red_flags.append("Bukti eksternal pasar masih sangat terbatas.")
    if source_results and not relevant_results:
        market_red_flags.append("Hasil pencarian eksternal belum cukup relevan dengan positioning bisnis.")
    if relevant_results and not has_market_coverage:
        market_red_flags.append("Bukti ukuran pasar dan pricing masih belum cukup kuat.")
    if market_results and len(selected_market_results) < len(market_results):
        market_red_flags.append("Bukti pasar yang ditemukan masih terlalu lebar dan belum cukup dekat dengan kategori bisnis inti.")
    if relevant_results and not has_competition_coverage:
        market_red_flags.append("Bukti kompetisi eksternal masih terbatas atau belum menyebut pemain pembanding yang jelas.")
    if not competition_names:
        market_red_flags.append("Kompetitor langsung belum teridentifikasi dengan jelas.")

    competition_risk = (
        f"Pasar {industry} di {geography} memiliki pemain pembanding yang perlu dianalisis lebih lanjut."
        if competition_names else
        (
            f"Alternatif kategori seperti {', '.join(substitute_names[:2])} menunjukkan risiko substitusi yang perlu dipetakan lebih jelas."
            if substitute_names else
            f"Risiko kompetisi untuk {company_name} belum tervalidasi kuat dari sumber eksternal."
        )
    )

    external_market_evidence = [
        {
            "title": item.get("title", "Tanpa judul"),
            "url": item.get("url", ""),
            "source": item.get("source", ""),
            "snippet": _clean_text(item.get("snippet", ""), 220),
        }
        for item in market_results
        if item in selected_market_results
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
        "substitutes": substitute_names,
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
