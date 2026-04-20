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

from app.graph.state import ReviewEngineState


GENERIC_TITLES = {
    "",
    "dokumen tanpa judul",
    "business plan",
    "rancangan bisnis",
    "business proposal",
    "proposal bisnis",
}

INDUSTRY_KEYWORDS = [
    ("logistics", "Logistik"),
    ("supply chain", "Logistik"),
    ("fintech", "Fintech"),
    ("payment", "Fintech"),
    ("edtech", "Pendidikan"),
    ("education", "Pendidikan"),
    ("school", "Pendidikan"),
    ("healthtech", "Kesehatan"),
    ("health", "Kesehatan"),
    ("medical", "Kesehatan"),
    ("agritech", "Pertanian"),
    ("agri", "Pertanian"),
    ("farming", "Pertanian"),
    ("saas", "SaaS"),
    ("software", "SaaS"),
    ("marketplace", "Marketplace"),
    ("e-commerce", "E-commerce"),
    ("ecommerce", "E-commerce"),
    ("retail", "Retail"),
    ("manufacturing", "Manufaktur"),
    ("manufacture", "Manufaktur"),
    ("energy", "Energi"),
    ("tourism", "Pariwisata"),
    ("travel", "Pariwisata"),
    ("hospitality", "Pariwisata"),
]

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
    "langganan",
    "subscription",
    "berlangganan",
    "paket",
    "biaya",
    "rp",
    "$",
    "usd",
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


def _split_sentences(text: str) -> list[str]:
    raw_sentences = re.split(r"(?<=[\.\!\?])\s+|\n{2,}", text)
    sentences = [re.sub(r"\s+", " ", sentence).strip(" -\n\t") for sentence in raw_sentences]
    return [sentence for sentence in sentences if len(sentence) >= 20]


def _extract_company_name(state: ReviewEngineState, text: str) -> str | None:
    for pattern in [
        r"(?:nama perusahaan|company name|nama usaha|nama startup)\s*[:\-]\s*([^\n]{3,80})",
        r"(?:perusahaan ini bernama|startup ini bernama)\s+([A-Z][^\n\.,]{2,60})",
    ]:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip(" .:-")

    title = (state.get("title") or "").strip()
    if title.lower() not in GENERIC_TITLES:
        return title
    return None


def _extract_industry(text: str, keywords: list[str]) -> str | None:
    lowered = f"{text.lower()} {' '.join(keywords).lower()}"
    for needle, label in INDUSTRY_KEYWORDS:
        if needle in lowered:
            return label
    return None


def _extract_target_customer(text: str) -> list[str]:
    candidates: list[str] = []
    for pattern in [
        r"(?:target customer|target market|segmen pelanggan|pelanggan target|pasar sasaran)\s*[:\-]\s*([^\n\.]{5,180})",
        r"(?:target pengguna adalah|target pelanggan adalah|menyasar)\s+([^\n\.]{5,180})",
    ]:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            captured = match.group(1).strip()
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
            return match.group(1).strip(" .:-")

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


def _extract_money_phrase(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None
    snippet = match.group(1).strip(" .:-")
    currency_match = re.search(
        r"(?:(?:rp|idr|usd|\$)\s?[\d\.,]+(?:\s?(?:juta|miliar|triliun|million|billion))?|[\d\.,]+\s?(?:juta|miliar|triliun)\s?(?:rupiah|idr)?)",
        snippet,
        re.IGNORECASE,
    )
    return currency_match.group(0).strip() if currency_match else snippet[:80]


def _extract_funding_ask(text: str) -> str | None:
    for pattern in [
        r"(?:funding ask|pendanaan yang dicari|kebutuhan pendanaan|investasi yang dibutuhkan|membutuhkan dana(?: sebesar)?)\s*[:\-]?\s*([^\n\.]{5,120})",
        r"(?:kami mencari pendanaan sebesar|target pendanaan sebesar)\s+([^\n\.]{5,120})",
    ]:
        funding = _extract_money_phrase(text, pattern)
        if funding:
            return funding
    return None


def _extract_signal_sentences(text: str, hints: list[str], max_items: int) -> list[str]:
    sentences = _split_sentences(text)
    matches = [
        sentence for sentence in sentences
        if any(hint in sentence.lower() for hint in hints) and any(ch.isdigit() for ch in sentence)
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
    industry = _extract_industry(text, keywords)
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
