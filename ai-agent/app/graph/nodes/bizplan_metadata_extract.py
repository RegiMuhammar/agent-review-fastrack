"""
bizplan_metadata_extract.py - Ekstraksi metadata khusus business plan
====================================================================
Menangkap sinyal bisnis yang tidak tercakup oleh metadata akademik umum.

Desain:
- Heuristik deterministik terlebih dahulu agar stabil dan mudah diuji.
- Fokus pada field yang relevan untuk founder, investor, dan frontend.
- Semua nilai string yang dihasilkan ditulis dalam Bahasa Indonesia.
"""

from __future__ import annotations

import re
from collections import defaultdict

from app.graph.state import ReviewEngineState


GENERIC_TITLES = {
    "",
    "dokumen tanpa judul",
    "business plan",
    "rancangan bisnis",
    "business proposal",
    "proposal bisnis",
}

INDUSTRY_SIGNALS = {
    "Pendidikan": [
        "edtech",
        "education technology",
        "education",
        "school",
        "kampus",
        "campus",
        "university",
        "student",
        "learning",
        "pembelajaran",
    ],
    "SaaS": [
        "saas",
        "software as a service",
        "software",
        "dashboard",
        "platform",
        "subscription",
    ],
    "Logistik": [
        "logistics",
        "logistik",
        "supply chain",
        "fleet",
        "delivery",
        "freight",
        "warehouse",
    ],
    "Fintech": [
        "fintech",
        "payment",
        "lending",
        "banking",
        "wallet",
    ],
    "Kesehatan": [
        "healthtech",
        "health care",
        "health",
        "medical",
        "klinik",
        "rumah sakit",
    ],
    "Pertanian": [
        "agritech",
        "agri",
        "farming",
        "pertanian",
        "petani",
    ],
    "Marketplace": [
        "marketplace",
        "two-sided",
        "seller",
        "merchant",
    ],
    "E-commerce": [
        "e-commerce",
        "ecommerce",
        "online retail",
        "retail tech",
    ],
    "Manufaktur": [
        "manufacturing",
        "manufacture",
        "factory",
        "industrial",
    ],
    "Energi": [
        "energy",
        "renewable",
        "solar",
        "power",
    ],
    "Pariwisata": [
        "tourism",
        "travel",
        "hospitality",
        "hotel",
    ],
}

INDUSTRY_PRIORITY = {
    "Pendidikan": 10,
    "Kesehatan": 9,
    "Pertanian": 8,
    "Fintech": 7,
    "Logistik": 6,
    "Marketplace": 5,
    "E-commerce": 4,
    "Manufaktur": 3,
    "Energi": 2,
    "Pariwisata": 1,
    "SaaS": 0,
}

BUSINESS_STAGE_PATTERNS = [
    (r"\bpre[- ]seed\b", "Pre-seed"),
    (r"\bseed\b", "Seed"),
    (r"\bseries\s*a\b", "Series A"),
    (r"\bseries\s*b\b", "Series B"),
    (r"\bseries\s*c\b", "Series C"),
    (r"\bpilot\b", "Pilot"),
    (r"\bmvp\b", "MVP"),
    (r"\bprototype\b", "Prototipe"),
    (r"\bearly[- ]stage\b", "Tahap awal"),
    (r"\bgrowth\b", "Growth"),
    (r"\bscale[- ]up\b", "Scale-up"),
    (r"\bbootstrapp?ed\b", "Bootstrap"),
]

GEOGRAPHY_KEYWORDS = [
    "indonesia",
    "jakarta",
    "bandung",
    "surabaya",
    "asia tenggara",
    "southeast asia",
    "singapore",
    "malaysia",
    "thailand",
    "vietnam",
    "asia",
    "global",
    "nasional",
]

TRACTION_HINTS = [
    "pengguna",
    "pelanggan",
    "customer",
    "users",
    "mrr",
    "arr",
    "gmv",
    "pilot",
    "mitra",
    "partnership",
    "pertumbuhan",
    "growth",
    "retention",
    "loi",
]

PRICING_HINTS = [
    "harga",
    "pricing",
    "price",
    "langganan",
    "subscription",
    "berlangganan",
    "paket",
    "biaya",
    "rp",
    "$",
    "usd",
    "starter",
    "growth",
    "enterprise",
    "per bulan",
    "per tahun",
]

PRICING_STRONG_HINTS = [
    "harga",
    "pricing",
    "price",
    "langganan",
    "subscription",
    "berlangganan",
    "paket",
    "tarif",
    "starter",
    "growth",
    "enterprise",
    "fee",
    "license",
    "lisensi",
]

NON_PRICING_METRIC_HINTS = [
    "tam",
    "sam",
    "som",
    "mrr",
    "arr",
    "gmv",
    "tpv",
    "cac",
    "ltv",
    "burn rate",
    "monthly burn",
    "cash burn",
    "runway",
    "gross margin",
    "margin kotor",
    "revenue",
    "pendapatan",
]

METADATA_LABEL_PATTERN = re.compile(
    r"\b(?:industry|industri|geography|geografi|business stage|tahap bisnis|funding ask|pendanaan|target customer|target pelanggan|company name|nama perusahaan)\b\s*:",
    re.IGNORECASE,
)

OCR_ARTIFACT_HINTS = [
    "start of picture text",
    "end of picture text",
    "picture text",
    "image text",
    "ocr text",
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
        print(f"[bizplan_metadata_extract][log_step] log gagal (diabaikan): {exc}")


def _unique_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = item.strip()
        key = normalized.lower()
        if not normalized or key in seen:
            continue
        seen.add(key)
        result.append(normalized)
    return result


def _to_slug(value: str | None) -> str | None:
    if not value:
        return None
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or None


def _truncate_at_metadata_label(text: str) -> str:
    if not text:
        return ""
    match = METADATA_LABEL_PATTERN.search(text)
    return text[:match.start()].strip(" .:-|") if match else text.strip(" .:-|")


def _sanitize_company_candidate(candidate: str | None) -> str | None:
    if not candidate:
        return None

    candidate = re.sub(r"\s+", " ", candidate).strip(" .:-|")
    candidate = _truncate_at_metadata_label(candidate)
    candidate = re.split(r"\s{2,}|[|]", candidate)[0].strip(" .:-|")
    candidate = candidate[:80].strip(" .:-|")

    if not candidate:
        return None

    lowered = candidate.lower()
    if lowered in GENERIC_TITLES:
        return None
    if any(token in lowered for token in ["industry:", "geography:", "funding ask:", "target customer:"]):
        return None

    words = candidate.split()
    if len(words) > 8:
        return None
    return candidate


def _split_sentences(text: str) -> list[str]:
    raw_sentences = re.split(r"(?<=[\.\!\?])\s+|\n{2,}", text)
    sentences = [re.sub(r"\s+", " ", sentence).strip(" -\n\t") for sentence in raw_sentences]
    return [sentence for sentence in sentences if len(sentence) >= 20]


def _is_signal_noise(sentence: str) -> bool:
    lowered = sentence.lower()
    if any(hint in lowered for hint in OCR_ARTIFACT_HINTS):
        return True
    if "<br>" in lowered:
        return True

    metric_tokens = sum(1 for token in ["mrr", "arr", "gmv", "loi", "cac", "ltv"] if token in lowered)
    numeric_tokens = len(re.findall(r"\d", sentence))
    if metric_tokens >= 3 and numeric_tokens >= 4 and len(sentence.split()) <= 18:
        return True
    return False


def _looks_like_pricing_sentence(sentence: str) -> bool:
    lowered = sentence.lower()
    has_strong_keyword = any(hint in lowered for hint in PRICING_STRONG_HINTS)
    has_currency = bool(re.search(r"(?:rp|idr|usd|\$)\s?[\d]+(?:[\.,]\d+)?", lowered))
    has_price_shape = bool(re.search(r"\b(?:per|/)\s*(?:bulan|month|tahun|year)\b", lowered))
    has_non_pricing_metric = any(hint in lowered for hint in NON_PRICING_METRIC_HINTS)
    if has_non_pricing_metric and not has_strong_keyword:
        return False
    return has_strong_keyword or (has_currency and has_price_shape and not has_non_pricing_metric)


def _extract_company_name(state: ReviewEngineState, text: str) -> str | None:
    for pattern in [
        r"(?:nama perusahaan|company name|nama usaha|nama startup)\s*[:\-]\s*([^\n]{3,80})",
        r"(?:perusahaan ini bernama|startup ini bernama)\s+([A-Z][^\n\.,]{2,60})",
    ]:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            candidate = _sanitize_company_candidate(match.group(1))
            if candidate:
                return candidate

    first_non_empty_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
    candidate = _sanitize_company_candidate(first_non_empty_line.lstrip("#").strip())
    if candidate:
        return candidate

    title = _sanitize_company_candidate((state.get("title") or "").strip())
    if title:
        return title
    return None


def _score_industry_phrase(phrase: str, weight: int, scores: dict[str, int]) -> None:
    lowered = phrase.lower()
    for label, needles in INDUSTRY_SIGNALS.items():
        for needle in needles:
            if needle in lowered:
                scores[label] += weight


def _extract_industry(text: str, keywords: list[str], title: str | None, document_head: str) -> str | None:
    scores: dict[str, int] = defaultdict(int)

    for pattern in [
        r"(?:industry|industri|sector|bidang)\s*[:\-]\s*([^\n]{3,120})",
    ]:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            _score_industry_phrase(match.group(1), 6, scores)

    if title:
        _score_industry_phrase(title, 3, scores)

    _score_industry_phrase(document_head[:2000], 2, scores)
    _score_industry_phrase(" ".join(keywords), 3, scores)
    _score_industry_phrase(text[:5000], 1, scores)

    if not scores:
        return None

    return sorted(
        scores.items(),
        key=lambda item: (item[1], INDUSTRY_PRIORITY.get(item[0], -1)),
        reverse=True,
    )[0][0]


def _clean_money_snippet(snippet: str) -> str:
    snippet = re.sub(r"\s+", " ", snippet).strip(" .:-")
    snippet = _truncate_at_metadata_label(snippet)
    return snippet[:100].strip(" .:-")


def _extract_money_phrase(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None

    snippet = _clean_money_snippet(match.group(1))
    if not snippet:
        return None

    currency_match = re.search(
        r"(?:(?:rp|idr|usd|\$)\s?[\d]+(?:[\.,]\d+)?(?:\s?(?:juta|miliar|triliun|million|billion))?|[\d]+(?:[\.,]\d+)?\s?(?:juta|miliar|triliun|million|billion)\s?(?:rupiah|idr)?)",
        snippet,
        re.IGNORECASE,
    )
    if not currency_match:
        return None

    start = currency_match.start()
    phrase = snippet[start:].strip(" .:-")
    return phrase[:100].strip(" .:-")


def _extract_target_customer(text: str) -> list[str]:
    candidates: list[str] = []
    for pattern in [
        r"(?:target customer|target market|segmen pelanggan|pelanggan target|pasar sasaran)\s*[:\-]\s*([^\n\.]{5,180})",
        r"(?:target pengguna adalah|target pelanggan adalah|menyasar)\s+([^\n\.]{5,180})",
    ]:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            captured = _truncate_at_metadata_label(match.group(1).strip())
            parts = re.split(r",|/| dan | serta ", captured)
            candidates.extend(part.strip(" .:-") for part in parts if len(part.strip()) >= 3)

    return _unique_keep_order(candidates)[:5]


def _extract_geography(text: str) -> str | None:
    for pattern in [
        r"(?:geografi|wilayah target|target area|target wilayah|fokus wilayah)\s*[:\-]\s*([^\n\.]{3,80})",
        r"(?:beroperasi di|fokus di|pasar utama di)\s+([^\n\.]{3,80})",
    ]:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return _truncate_at_metadata_label(match.group(1)).strip(" .:-")

    lowered = text.lower()
    for keyword in GEOGRAPHY_KEYWORDS:
        if keyword in lowered:
            return keyword.title() if keyword != "asia tenggara" else "Asia Tenggara"
    return None


def _extract_business_stage(text: str) -> str | None:
    lowered = text.lower()
    for pattern, label in BUSINESS_STAGE_PATTERNS:
        if re.search(pattern, lowered):
            return label
    return None


def _extract_funding_ask(text: str) -> str | None:
    for pattern in [
        r"(?:funding ask|pendanaan yang dicari|kebutuhan pendanaan|investasi yang dibutuhkan|membutuhkan dana(?: sebesar)?)\s*[:\-]?\s*([^\n]{5,120})",
        r"(?:kami mencari pendanaan sebesar|target pendanaan sebesar)\s+([^\n]{5,120})",
    ]:
        funding = _extract_money_phrase(text, pattern)
        if funding:
            return funding
    return None


def _extract_signal_sentences(text: str, hints: list[str], max_items: int) -> list[str]:
    sentences = _split_sentences(text)
    matches = [
        sentence for sentence in sentences
        if (
            _looks_like_pricing_sentence(sentence)
            if hints is PRICING_HINTS
            else any(hint in sentence.lower() for hint in hints)
        )
        and any(ch.isdigit() for ch in sentence)
        and not _is_signal_noise(sentence)
    ]
    return _unique_keep_order(matches)[:max_items]


async def bizplan_metadata_extract_node(state: ReviewEngineState) -> dict:
    """
    Ekstraksi metadata khusus business plan.

    Output:
    - company_name, industry, geography, business_stage
    - target_customer, funding_ask, traction_signals, pricing_signals
    - domain/sub_domain untuk menjaga kompatibilitas output lama
    """
    analysis_id = state.get("analysis_id", "unknown")
    raw_markdown = state.get("raw_markdown") or ""
    document_head = state.get("document_head") or ""
    keywords = state.get("keywords") or []
    title = state.get("title")

    print("\n[bizplan_metadata_extract] Memulai ekstraksi metadata business plan...")
    _safe_log(analysis_id, "bizplan_metadata", "processing", "Mengekstrak metadata khusus business plan...")

    text = f"{document_head}\n\n{raw_markdown[:5000]}".strip()
    if not text:
        _safe_log(analysis_id, "bizplan_metadata", "done", "Metadata business plan: skip (dokumen kosong)")
        return {
            "company_name": state.get("title") or None,
            "industry": None,
            "target_customer": [],
            "geography": None,
            "business_stage": None,
            "funding_ask": None,
            "traction_signals": [],
            "pricing_signals": [],
            "domain": "business",
            "sub_domain": "general_business",
        }

    company_name = _extract_company_name(state, text)
    industry = _extract_industry(text, keywords, title, document_head)
    target_customer = _extract_target_customer(text)
    geography = _extract_geography(text)
    business_stage = _extract_business_stage(text)
    funding_ask = _extract_funding_ask(text)
    traction_signals = _extract_signal_sentences(text, TRACTION_HINTS, max_items=4)
    pricing_signals = _extract_signal_sentences(text, PRICING_HINTS, max_items=4)

    sub_domain = _to_slug(industry) or "general_business"

    print(f"[bizplan_metadata_extract] Company: {company_name or 'N/A'}")
    print(f"[bizplan_metadata_extract] Industry: {industry or 'N/A'} | Stage: {business_stage or 'N/A'}")
    print(f"[bizplan_metadata_extract] Target customer: {target_customer}")
    print(f"[bizplan_metadata_extract] Geography: {geography or 'N/A'} | Funding ask: {funding_ask or 'N/A'}")

    _safe_log(
        analysis_id,
        "bizplan_metadata",
        "done",
        f"Metadata business plan siap - industri: {industry or 'umum'}, tahap: {business_stage or 'tidak diketahui'}",
    )

    return {
        "company_name": company_name,
        "industry": industry,
        "target_customer": target_customer,
        "geography": geography,
        "business_stage": business_stage,
        "funding_ask": funding_ask,
        "traction_signals": traction_signals,
        "pricing_signals": pricing_signals,
        "domain": "business",
        "sub_domain": sub_domain,
    }
