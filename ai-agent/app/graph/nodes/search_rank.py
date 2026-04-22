"""
search_rank.py — Search Ranking Node (Fase 6)
===============================================
Ranking dan seleksi referensi dari search_results.

Strategi 2-layer:
1. Heuristic scoring (cepat, tanpa LLM):
   - Keyword overlap antara title/snippet dengan paper title+keywords
   - Source weighting (scholar > arxiv > tavily)
   - Year recency bonus
   - Snippet length quality signal

2. LLM rerank (optional, hanya top-N kandidat):
   - Hanya jika ada cukup banyak kandidat (>5)
   - Menggunakan Groq untuk scoring relevansi
   - Fallback ke heuristic jika LLM gagal

Output:
- ranked_results : semua hasil terurut
- top_references : 3-5 terbaik untuk context LLM scoring

Flow: ... → search_execute → search_rank → research_agent → ...
"""

import json
import logging
import re
from urllib.parse import urlparse

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from app.graph.state import ReviewEngineState
from app.core.config import settings

logger = logging.getLogger(__name__)

# Berapa referensi teratas yang masuk ke context LLM
TOP_K = 5

# Threshold minimal untuk masuk top_references
MIN_RELEVANCE_THRESHOLD = 0.3
BIZPLAN_MIN_RELEVANCE_THRESHOLD = 0.45

ROLE_HINTS = {
    "competition": [
        "competitor",
        "competitors",
        "competition",
        "competitive",
        "rival",
        "alternative",
        "alternatives",
        "pesaing",
        "kompetitor",
        "kompetisi",
    ],
    "pricing": [
        "pricing",
        "price",
        "harga",
        "tarif",
        "benchmark",
        "subscription",
        "fee",
        "license",
        "lisensi",
    ],
    "market": [
        "market",
        "pasar",
        "industry",
        "industri",
        "growth",
        "adoption",
        "permintaan",
        "benchmark",
    ],
}

DISCOVERY_COMPETITION_HINTS = [
    "top ",
    "best ",
    "leading ",
    "alternatives to",
    "alternative to",
    "vs ",
    "compare",
    "comparison",
    "vendor",
    "vendors",
    "provider",
    "providers",
]

PRODUCT_CATEGORY_HINTS = [
    "software",
    "platform",
    "system",
    "suite",
    "dashboard",
    "erp",
    "solution",
    "solutions",
    "tool",
    "tools",
    "app",
]

SOFTWARE_MARKET_HINTS = [
    "software",
    "platform",
    "dashboard",
    "erp",
    "app",
    "saas",
]

COMPETITION_FALSE_POSITIVE_HINTS = [
    "competitive landscape",
    "market overview",
    "market segmentation",
]

NOISE_BIZPLAN_HINTS = [
    "investor",
    "investors",
    "venture capital",
    "consulting",
    "consultancy",
    "payroll",
    "hris",
    "attendance",
    "home education",
    "homeschool",
]

NON_PRODUCT_PRICING_HINTS = [
    "consulting",
    "consultancy",
    "consultant",
    "csr",
    "packaging",
    "commodity",
    "plastic",
    "supply chain",
]

GENERIC_DIRECTORY_TITLE_HINTS = [
    "companies in",
    "company in",
    "services in",
    "service providers",
    "agencies",
    "agency",
    "firms",
    "top 5",
    "top 10",
    "top 20",
    "top 50",
    "list of",
]

MARKET_REPORT_HINTS = [
    "market size",
    "market report",
    "industry analysis",
    "forecast",
    "cagr",
    "market growth",
]

INDUSTRY_TERMS = {
    "Pendidikan": ["education", "edtech", "school", "campus", "university", "student", "learning"],
    "SaaS": ["saas", "software", "platform", "dashboard", "subscription"],
    "Logistik": ["logistics", "logistic", "delivery", "fleet", "warehouse", "freight", "supply chain"],
    "Fintech": ["fintech", "payment", "lending", "wallet", "banking"],
    "Kesehatan": ["health", "healthtech", "medical", "clinic", "hospital"],
    "Pertanian": ["agri", "agritech", "farm", "farming", "crop", "agriculture"],
}

OFF_POSITION_HINTS = [
    "warehouse",
    "fleet",
    "freight",
    "shipping",
    "manufacturing",
    "mining",
    "oil and gas",
]

LOW_SIGNAL_DOMAIN_HINTS = [
    "linkedin.com",
    "medium.com",
    "facebook.com",
    "instagram.com",
    "tiktok.com",
    "youtube.com",
    "x.com",
    "twitter.com",
    "pinterest.com",
]

TRUSTED_BIZPLAN_DOMAIN_HINTS = [
    "statista.com",
    "unesco.org",
    ".gov",
    ".edu",
    ".ac.",
    "imarcgroup.com",
    "gmiresearch.com",
    "nexdigm.com",
    "openeducat.org",
    "marketresearch.com",
    "kenresearch.com",
]

SOFTWARE_DIRECTORY_DOMAIN_HINTS = [
    "g2.com",
    "getapp.com",
    "capterra.com",
    "softwareadvice.com",
    "sourceforge.net",
    "crozdesk.com",
    "trustradius.com",
    "slashdot.org",
    "openeducat.org",
]

PRESS_RELEASE_DOMAIN_HINTS = [
    "openpr.com",
    "prnewswire.com",
    "globenewswire.com",
    "einnews.com",
]

BIZPLAN_EXCLUDED_DOMAIN_HINTS = [
    "linkedin.com",
    "facebook.com",
    "instagram.com",
    "tiktok.com",
    "pinterest.com",
]

# ── HEURISTIC SCORING ────────────────────────────────────────────────────────

def _normalize(text: str) -> set[str]:
    """Normalize teks ke set of lowercase words."""
    return set(re.sub(r"[^\w\s]", "", text.lower()).split())


def _safe_preview(text: str, limit: int = 60) -> str:
    preview = (text or "")[:limit]
    return preview.encode("cp1252", errors="replace").decode("cp1252", errors="replace")


def _token_list(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def _bizplan_phrases(state: ReviewEngineState) -> list[str]:
    phrases: list[str] = []
    for value in [
        state.get("company_name"),
        state.get("industry"),
        state.get("title"),
    ]:
        if isinstance(value, str) and value.strip():
            phrases.append(value.strip())

    for collection_key in ["target_customer", "keywords", "revenue_model", "pricing_signals"]:
        for item in state.get(collection_key) or []:
            if isinstance(item, str) and item.strip():
                phrases.append(item.strip())

    industry = state.get("industry") or ""
    for term in INDUSTRY_TERMS.get(industry, []):
        phrases.append(term)

    deduped: list[str] = []
    seen: set[str] = set()
    for phrase in phrases:
        normalized = phrase.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(phrase)
    return deduped


def _phrase_overlap_score(haystack: str, phrases: list[str], max_score: float) -> float:
    score = 0.0
    matched = 0
    haystack_tokens = set(_token_list(haystack))
    for phrase in phrases:
        lowered = phrase.lower()
        if lowered in haystack:
            matched += 1
            score += 0.12
            continue

        phrase_tokens = [token for token in _token_list(phrase) if len(token) >= 4]
        if phrase_tokens and len(haystack_tokens & set(phrase_tokens)) >= min(2, len(phrase_tokens)):
            matched += 1
            score += 0.08
        if matched >= 4:
            break
    return min(score, max_score)


def _classify_bizplan_reference_role(result: dict) -> str:
    haystack = f"{result.get('title', '')} {result.get('snippet', '')}".lower()
    if any(token in haystack for token in COMPETITION_FALSE_POSITIVE_HINTS) and "market" in haystack:
        return "market"
    if _looks_like_business_competition(result):
        return "competition"
    if _looks_like_competitor_landscape(result):
        return "competition"
    if _looks_like_pricing_reference(result):
        return "pricing"
    if any(token in haystack for token in ROLE_HINTS["market"]):
        return "market"
    return "general"


def _looks_like_business_competition(result: dict) -> bool:
    title = (result.get("title") or "").lower()
    snippet = (result.get("snippet") or "").lower()
    url = (result.get("url") or "").lower()
    haystack = f"{title} {snippet}"
    has_explicit_business_term = any(token in haystack for token in ["competitor", "competitors", "alternative", "alternatives", "rival"])
    has_generic_competition_term = any(token in haystack for token in ["competition", "competitive", "kompetisi", "kompetitor"])
    has_product_context = any(hint in haystack for hint in PRODUCT_CATEGORY_HINTS) or any(
        hint in url for hint in ["/compare", "/comparison", "/alternatives", "/vendors", "/vendor", "/category", "/directory"]
    )
    has_customer_context = any(pattern in haystack for pattern in ["campus", "university", "school", "software", "platform", "dashboard"])
    return (has_explicit_business_term and (has_product_context or has_customer_context)) or (
        has_generic_competition_term and has_product_context
    )


def _looks_like_pricing_reference(result: dict) -> bool:
    title = (result.get("title") or "").lower()
    snippet = (result.get("snippet") or "").lower()
    url = (result.get("url") or "").lower()
    haystack = f"{title} {snippet}"
    has_pricing_term = any(token in haystack for token in ROLE_HINTS["pricing"])
    if any(hint in haystack for hint in NON_PRODUCT_PRICING_HINTS):
        return False
    has_pricing_context = (
        any(hint in haystack for hint in PRODUCT_CATEGORY_HINTS)
        or any(hint in url for hint in ["/pricing", "/plans", "/plan", "/subscription"])
        or any(token in haystack for token in ["per month", "per year", "monthly", "annual", "student", "plan"])
    )
    return has_pricing_term and has_pricing_context


def _looks_like_competitor_landscape(result: dict) -> bool:
    title = (result.get("title") or "").lower()
    snippet = (result.get("snippet") or "").lower()
    url = (result.get("url") or "").lower()
    haystack = f"{title} {snippet}"

    has_discovery_hint = any(hint in haystack for hint in DISCOVERY_COMPETITION_HINTS)
    has_product_hint = any(hint in haystack for hint in PRODUCT_CATEGORY_HINTS)
    if any(hint in haystack for hint in COMPETITION_FALSE_POSITIVE_HINTS):
        return False
    has_directory_hint = any(hint in url for hint in ["/compare", "/comparison", "/alternatives", "/vendors", "/vendor", "/category", "/directory"])
    has_directory_domain = any(hint in urlparse(url).netloc.lower() for hint in SOFTWARE_DIRECTORY_DOMAIN_HINTS)
    geography_patterns = [
        " in indonesia",
        " for universities",
        " for campuses",
        " higher education",
        " campus operations",
    ]
    has_context_hint = any(pattern in haystack for pattern in geography_patterns)

    if "alternatives to" in haystack or "alternative to" in haystack or " vs " in haystack:
        return True
    if has_product_hint and has_context_hint and (has_directory_hint or has_directory_domain):
        return True
    return has_discovery_hint and has_product_hint and has_context_hint


def _bizplan_noise_penalty(haystack: str, role: str, state: ReviewEngineState) -> float:
    penalty = 0.0
    customer_phrases = list(state.get("target_customer") or [])
    customer_phrases.extend(INDUSTRY_TERMS.get(state.get("industry") or "", []))
    customer_alignment = _phrase_overlap_score(haystack, customer_phrases, max_score=0.16)
    product_alignment = 0.08 if any(hint in haystack for hint in PRODUCT_CATEGORY_HINTS) else 0.0

    if any(hint in haystack for hint in NOISE_BIZPLAN_HINTS):
        penalty += 0.22
    if role == "general" and customer_alignment == 0 and product_alignment == 0:
        penalty += 0.18
    if role in {"competition", "pricing"} and product_alignment == 0:
        penalty += 0.14
    if role == "competition" and any(hint in haystack for hint in COMPETITION_FALSE_POSITIVE_HINTS):
        penalty += 0.22
    return penalty


def _bizplan_market_fit_score(haystack: str, state: ReviewEngineState) -> float:
    customer_terms = list(state.get("target_customer") or [])
    industry_terms = INDUSTRY_TERMS.get(state.get("industry") or "", [])
    customer_overlap = _phrase_overlap_score(haystack, customer_terms, max_score=0.18)
    industry_overlap = _phrase_overlap_score(haystack, industry_terms, max_score=0.18)
    product_score = 0.08 if any(hint in haystack for hint in SOFTWARE_MARKET_HINTS) else 0.0
    return round(min(customer_overlap + industry_overlap + product_score, 0.32), 3)


def _is_weak_bizplan_competition_reference(result: dict) -> bool:
    title = (result.get("title") or "").lower()
    snippet = (result.get("snippet") or "").lower()
    url = (result.get("url") or "").lower()
    haystack = f"{title} {snippet}"

    has_generic_directory_title = any(hint in title for hint in GENERIC_DIRECTORY_TITLE_HINTS)
    has_product_context = any(hint in haystack for hint in PRODUCT_CATEGORY_HINTS)
    has_vendor_url = any(hint in url for hint in ["/compare", "/comparison", "/alternatives", "/vendors", "/vendor", "/pricing"])
    has_explicit_vendor_names = bool(re.search(r"\b[A-Z][a-z0-9]+[A-Z][A-Za-z0-9]+\b", result.get("snippet", "") or ""))

    if has_generic_directory_title and not has_product_context:
        return True
    if has_generic_directory_title and not has_vendor_url and not has_explicit_vendor_names:
        return True
    return False


def _bizplan_domain_score(result: dict) -> float:
    url = (result.get("url") or "").lower()
    if not url:
        return 0.0
    domain = urlparse(url).netloc.lower()
    path = urlparse(url).path.lower()
    if any(hint in domain for hint in LOW_SIGNAL_DOMAIN_HINTS):
        return -0.18
    if any(hint in domain for hint in PRESS_RELEASE_DOMAIN_HINTS):
        return -0.16
    if any(hint in domain for hint in SOFTWARE_DIRECTORY_DOMAIN_HINTS):
        return 0.16
    if any(hint in domain for hint in TRUSTED_BIZPLAN_DOMAIN_HINTS):
        return 0.12
    if any(hint in path for hint in ["/pricing", "/compare", "/comparison", "/alternatives", "/software", "/vendors", "/vendor"]):
        return 0.1
    if domain.endswith(".org") or domain.endswith(".edu"):
        return 0.08
    return 0.0


def _is_excluded_bizplan_domain(result: dict) -> bool:
    url = (result.get("url") or "").lower()
    if not url:
        return False
    domain = urlparse(url).netloc.lower()
    return any(hint in domain for hint in BIZPLAN_EXCLUDED_DOMAIN_HINTS)


def _bizplan_reference_score(result: dict, state: ReviewEngineState, target_year: int | None) -> float:
    haystack = f"{result.get('title', '')} {result.get('snippet', '')}".lower()
    phrases = _bizplan_phrases(state)
    match_score = _phrase_overlap_score(haystack, phrases, max_score=0.45)

    geography = (state.get("geography") or "").lower()
    geography_score = 0.08 if geography and geography in haystack else 0.0

    role = _classify_bizplan_reference_role(result)
    role_score = {"market": 0.12, "competition": 0.12, "pricing": 0.1, "general": 0.04}[role]
    customer_score = _phrase_overlap_score(
        haystack,
        list(state.get("target_customer") or []) + INDUSTRY_TERMS.get(state.get("industry") or "", []),
        max_score=0.16,
    )
    product_score = 0.08 if any(hint in haystack for hint in PRODUCT_CATEGORY_HINTS) else 0.0
    market_fit_score = _bizplan_market_fit_score(haystack, state)
    market_report_bonus = 0.08 if role == "market" and market_fit_score >= 0.12 and any(
        hint in haystack for hint in MARKET_REPORT_HINTS
    ) else 0.0

    source_weights = {
        "semanticscholar": 0.12,
        "arxiv": 0.10,
        "tavily": 0.08,
    }
    source_score = source_weights.get(result.get("source", ""), 0.06)
    recency = _temporal_alignment_score(result.get("year"), target_year) * 0.08
    snippet_quality = min(len(result.get("snippet", "")) / 240, 1.0) * 0.08
    domain_score = _bizplan_domain_score(result)

    positive_overlap = match_score + geography_score + customer_score + product_score
    penalty = 0.0
    if positive_overlap < 0.18 and any(hint in haystack for hint in OFF_POSITION_HINTS):
        penalty = 0.18
    if role == "market":
        if market_fit_score < 0.08:
            penalty += 0.24
        elif market_fit_score < 0.14:
            penalty += 0.12
    if role == "competition" and _is_weak_bizplan_competition_reference(result):
        penalty += 0.24
    penalty += _bizplan_noise_penalty(haystack, role, state)

    score = positive_overlap + role_score + source_score + recency + snippet_quality + domain_score + market_report_bonus - penalty
    return round(max(min(score, 1.0), 0.0), 3)


def _select_bizplan_top_references(ranked_results: list[dict], threshold: float) -> list[dict]:
    selected: list[dict] = []
    selected_urls: set[str] = set()

    for role in ["market", "competition", "pricing"]:
        for result in ranked_results:
            if result.get("reference_role") != role:
                continue
            if result.get("relevance_score", 0.0) < threshold:
                continue
            if role == "market" and result.get("market_fit_score", 0.0) < 0.08:
                continue
            if role == "competition" and _is_weak_bizplan_competition_reference(result):
                continue
            if _is_excluded_bizplan_domain(result):
                continue
            url = result.get("url") or result.get("title")
            if url in selected_urls:
                continue
            selected.append(result)
            selected_urls.add(url)
            break

    for result in ranked_results:
        if result.get("relevance_score", 0.0) < threshold:
            continue
        if _is_excluded_bizplan_domain(result):
            continue
        if result.get("reference_role") == "competition" and _is_weak_bizplan_competition_reference(result):
            continue
        if result.get("reference_role") == "general" and result.get("relevance_score", 0.0) < threshold + 0.12:
            continue
        url = result.get("url") or result.get("title")
        if url in selected_urls:
            continue
        selected.append(result)
        selected_urls.add(url)
        if len(selected) >= TOP_K:
            break

    return selected[:TOP_K]


def _temporal_alignment_score(result_year: int | None, target_year: int | None) -> float:
    """
    Skor kesesuaian temporal relatif terhadap tahun paper target.

    Jika target_year tersedia, paper yang terbit di sekitar atau sebelum tahun target
    diprioritaskan dibanding paper yang jauh lebih baru.
    """
    if not result_year or not isinstance(result_year, int):
        return 0.5

    if not target_year or not isinstance(target_year, int):
        if result_year >= 2023:
            return 1.0
        if result_year >= 2020:
            return 0.7
        if result_year >= 2015:
            return 0.4
        return 0.2

    if result_year <= target_year:
        gap = target_year - result_year
        if gap <= 2:
            return 1.0
        if gap <= 5:
            return 0.8
        if gap <= 10:
            return 0.6
        return 0.4

    future_gap = result_year - target_year
    if future_gap <= 2:
        return 0.75
    if future_gap <= 5:
        return 0.55
    return 0.35


def _heuristic_score(
    result: dict,
    paper_words: set[str],
    paper_keywords: list[str],
    target_year: int | None,
) -> float:
    """
    Heuristic relevance score (0.0 - 1.0).

    Komponen:
    - keyword_overlap (0.4): seberapa banyak kata dari paper muncul di result
    - source_weight  (0.2): scholar > arxiv > tavily
    - recency_bonus  (0.2): paper terbaru lebih relevan
    - snippet_quality(0.2): snippet lebih panjang = lebih informatif
    """
    # 1. Keyword overlap
    result_words = _normalize(result.get("title", "") + " " + result.get("snippet", ""))
    if paper_words:
        overlap = len(paper_words & result_words) / max(len(paper_words), 1)
    else:
        overlap = 0.0
    keyword_overlap = min(overlap * 2, 1.0)  # boost karena biasanya overlap rendah

    # Bonus untuk exact keyword match
    keyword_bonus = 0.0
    for kw in paper_keywords:
        if kw.lower() in result.get("title", "").lower():
            keyword_bonus += 0.1
    keyword_bonus = min(keyword_bonus, 0.3)

    # 2. Source weight
    source_weights = {
        "semanticscholar": 0.9,
        "arxiv": 0.8,
        "tavily": 0.5,
    }
    source_score = source_weights.get(result.get("source", ""), 0.5)

    # 3. Temporal alignment
    recency = _temporal_alignment_score(result.get("year"), target_year)

    # 4. Snippet quality
    snippet_len = len(result.get("snippet", ""))
    snippet_quality = min(snippet_len / 300, 1.0)

    # Weighted sum
    score = (
        0.35 * (keyword_overlap + keyword_bonus) +
        0.20 * source_score +
        0.20 * recency +
        0.25 * snippet_quality
    )

    return round(min(score, 1.0), 3)


# ── LLM RERANK ───────────────────────────────────────────────────────────────

RERANK_SYSTEM_PROMPT = """Kamu adalah ahli ranking relevansi paper akademik.
Diberikan metadata paper target dan daftar hasil pencarian, berikan skor relevansi untuk setiap hasil.

Kriteria scoring (gabungkan menjadi skor 0.0-1.0):
- Relevansi topik: Apakah membahas masalah atau metode yang sama?
- Kesamaan metodologi: Apakah menggunakan pendekatan serupa?
- Overlap domain: Apakah di bidang akademik yang sama?
- Potensi sebagai referensi: Apakah ini bisa menjadi sitasi yang bermakna?

Jawab HANYA dengan JSON valid (tanpa markdown fences):
{
  "scores": [
    {"index": 0, "score": 0.95, "reason": "satu kalimat"},
    {"index": 1, "score": 0.72, "reason": "satu kalimat"}
  ]
}

Index sesuai posisi di daftar input (0-based).
Score: 0.0 = tidak relevan, 1.0 = sangat relevan.
"""

BIZPLAN_RERANK_SYSTEM_PROMPT = """Kamu adalah analis VC yang sedang mereranking referensi eksternal untuk validasi business plan.
Diberikan snapshot bisnis dan daftar hasil pencarian web, beri skor relevansi untuk setiap hasil.

Kriteria scoring (gabungkan menjadi skor 0.0-1.0):
- Kesesuaian wedge bisnis: seberapa dekat dengan produk, customer, dan positioning startup
- Kegunaan validasi pasar: apakah membantu memvalidasi ukuran pasar atau demand
- Kegunaan validasi pricing: apakah membantu memahami benchmark harga atau monetisasi
- Kegunaan validasi kompetisi: apakah menyebut pemain pembanding, alternatif, atau lanskap kompetitor yang nyata
- Kesesuaian geografi: utamakan hasil yang relevan dengan wilayah target

Turunkan skor jika hasil terlalu generik, terlalu akademik tanpa kaitan pasar, atau tidak membantu investor memahami kompetisi/pricing.

Jawab HANYA dengan JSON valid (tanpa markdown fences):
{
  "scores": [
    {"index": 0, "score": 0.95, "reason": "satu kalimat"},
    {"index": 1, "score": 0.40, "reason": "satu kalimat"}
  ]
}
"""


async def _llm_rerank(candidates: list[dict], state: ReviewEngineState) -> list[dict] | None:
    """
    LLM rerank untuk kandidat teratas. Return None jika gagal.
    """
    doc_type = state.get("doc_type", "research")
    title = state.get("title") or ""
    abstract = state.get("abstract") or ""
    domain = state.get("domain") or "general"
    company_name = state.get("company_name") or title
    industry = state.get("industry") or ""
    geography = state.get("geography") or ""
    target_customer = ", ".join((state.get("target_customer") or [])[:3])
    revenue_model = ", ".join((state.get("revenue_model") or [])[:3])
    pricing_signals = ", ".join((state.get("pricing_signals") or [])[:2])

    # Build compact list
    results_text = "\n".join(
        f"[{i}] Title: {r['title']}\n"
        f"    Source: {r['source']} | Year: {r.get('year', 'N/A')}\n"
        f"    Snippet: {r['snippet'][:200]}"
        for i, r in enumerate(candidates)
    )

    if doc_type == "bizplan":
        system_prompt = BIZPLAN_RERANK_SYSTEM_PROMPT
        user_content = (
            f"Business Snapshot:\n"
            f"Company: {company_name}\n"
            f"Industry: {industry}\n"
            f"Geography: {geography}\n"
            f"Target Customer: {target_customer}\n"
            f"Revenue Model: {revenue_model}\n"
            f"Pricing Signals: {pricing_signals}\n\n"
            f"Hasil Pencarian untuk Di-ranking:\n{results_text}"
        )
    else:
        system_prompt = RERANK_SYSTEM_PROMPT
        user_content = (
            f"Paper Target:\nTitle: {title}\nDomain: {domain}\n"
            f"Abstract: {abstract[:600]}\n\n"
            f"Hasil Pencarian untuk Di-ranking:\n{results_text}"
        )

    try:
        llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0,
            api_key=settings.GROQ_API_KEY,
        )

        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_content),
        ])

        raw = response.content.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        data = json.loads(raw)

        scores = data.get("scores", [])

        # Apply LLM scores
        reranked = list(candidates)
        for s in scores:
            idx = s.get("index", -1)
            score = float(s.get("score", 0.5))
            if 0 <= idx < len(reranked):
                if doc_type == "bizplan":
                    base_score = float(reranked[idx].get("relevance_score", 0.5))
                    score = round((base_score * 0.7) + (score * 0.3), 3)
                reranked[idx] = {**reranked[idx], "relevance_score": score}

        # Sort descending
        reranked.sort(key=lambda x: x["relevance_score"], reverse=True)
        return reranked

    except Exception as e:
        logger.warning(f"LLM rerank gagal (fallback ke heuristic): {e}")
        return None


# ── HELPERS ──────────────────────────────────────────────────────────────────

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
        print(f"[search_rank][log_step] log gagal (diabaikan): {exc}")


# ── NODE UTAMA ───────────────────────────────────────────────────────────────

async def search_rank_node(state: ReviewEngineState) -> dict:
    """
    LangGraph node: Ranking dan seleksi referensi.

    Input dari state:
        - search_results   : list[dict] dari search_execute
        - title, abstract, keywords (untuk scoring relevansi)
        - domain (untuk context)

    Output (di-merge ke state):
        - ranked_results   : semua hasil terurut
        - top_references   : 3-5 terbaik
    """
    analysis_id = state.get("analysis_id", "unknown")
    search_results = state.get("search_results") or []
    doc_type = state.get("doc_type", "research")

    print(f"\n[search_rank] Memulai ranking {len(search_results)} hasil...")
    _safe_log(analysis_id, "ranking", "processing", f"Meranking {len(search_results)} referensi...")

    # ─── Guard: tidak ada results ─────────────────────────────────────────
    if not search_results:
        print("[search_rank] Tidak ada search results, skip ranking")
        _safe_log(analysis_id, "ranking", "done", "Ranking: skip (tidak ada hasil)")
        return {"ranked_results": [], "top_references": []}

    # ─── Step 1: Heuristic scoring ────────────────────────────────────────
    paper_title = state.get("title") or ""
    paper_keywords = state.get("keywords") or []
    target_year = state.get("year")
    paper_words = _normalize(paper_title + " " + " ".join(paper_keywords))

    scored = []
    for r in search_results:
        if doc_type == "bizplan":
            h_score = _bizplan_reference_score(r, state, target_year)
            scored.append({
                **r,
                "reference_role": _classify_bizplan_reference_role(r),
                "market_fit_score": _bizplan_market_fit_score(
                    f"{r.get('title', '')} {r.get('snippet', '')}".lower(),
                    state,
                ),
                "relevance_score": h_score,
            })
        else:
            h_score = _heuristic_score(r, paper_words, paper_keywords, target_year)
            scored.append({**r, "relevance_score": h_score})

    # Sort descending
    scored.sort(key=lambda x: x["relevance_score"], reverse=True)

    print(f"[search_rank] Heuristic scoring selesai:")
    for i, r in enumerate(scored[:5]):
        print(f"  #{i+1} [{r['relevance_score']:.3f}] {_safe_preview(r['title'])}")

    # ─── Step 2: Optional LLM rerank (hanya jika >5 kandidat) ────────────
    use_llm_rerank = len(scored) > 5

    if use_llm_rerank:
        # Hanya rerank top 10 kandidat (hemat token)
        top_candidates = scored[:10]
        print(f"[search_rank] LLM rerank untuk top {len(top_candidates)} kandidat...")

        reranked = await _llm_rerank(top_candidates, state)

        if reranked is not None:
            # Gabungkan: reranked top + sisa heuristic
            reranked_ids = {r.get("url") for r in reranked}
            remaining = [r for r in scored if r.get("url") not in reranked_ids]
            ranked_results = reranked + remaining
            print(f"[search_rank] LLM rerank berhasil")
        else:
            ranked_results = scored
            print(f"[search_rank] LLM rerank gagal, gunakan heuristic")
    else:
        ranked_results = scored
        print(f"[search_rank] Skip LLM rerank ({len(scored)} kandidat ≤ 5)")

    # ─── Step 3: Select top references ────────────────────────────────────
    if doc_type == "bizplan":
        top_references = _select_bizplan_top_references(ranked_results, BIZPLAN_MIN_RELEVANCE_THRESHOLD)
    else:
        top_references = [
            r for r in ranked_results[:TOP_K]
            if r["relevance_score"] >= MIN_RELEVANCE_THRESHOLD
        ]

    summary = f"Ranking selesai — {len(top_references)} referensi terpilih dari {len(ranked_results)}"
    print(f"[search_rank] {summary}")
    if top_references:
        print(f"[search_rank] Top referensi:")
        for i, r in enumerate(top_references):
            print(f"  #{i+1} [{r['relevance_score']:.3f}] [{r['source']}] {_safe_preview(r['title'])}")

    _safe_log(analysis_id, "ranking", "done", summary)

    return {
        "ranked_results": ranked_results,
        "top_references": top_references,
    }
