"""
bizplan_financials.py - Ekstraksi sinyal finansial business plan
================================================================
Mengambil metrik finansial yang paling berguna untuk review ala investor:
- model pendapatan
- sinyal harga
- unit economics
- burn, runway, dan break-even

Node ini memakai heuristik agar stabil, murah, dan aman untuk regression test.
"""

from __future__ import annotations

import re

from app.graph.state import ReviewEngineState


REVENUE_MODEL_PATTERNS = [
    ("subscription", "Langganan"),
    ("langganan", "Langganan"),
    ("berlangganan", "Langganan"),
    ("freemium", "Freemium"),
    ("commission", "Komisi"),
    ("komisi", "Komisi"),
    ("take rate", "Take rate"),
    ("transaction fee", "Biaya transaksi"),
    ("biaya transaksi", "Biaya transaksi"),
    ("license", "Lisensi"),
    ("lisensi", "Lisensi"),
    ("ads", "Iklan"),
    ("advertising", "Iklan"),
    ("project-based", "Proyek"),
    ("jasa implementasi", "Jasa implementasi"),
    ("setup fee", "Biaya setup"),
]

PRICING_HINTS = [
    "harga",
    "pricing",
    "langganan",
    "subscription",
    "paket",
    "biaya",
    "tarif",
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
        print(f"[bizplan_financials][log_step] log gagal (diabaikan): {exc}")


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


def _split_sentences(text: str) -> list[str]:
    raw_sentences = re.split(r"(?<=[\.\!\?])\s+|\n{2,}", text)
    sentences = [re.sub(r"\s+", " ", sentence).strip(" -\n\t") for sentence in raw_sentences]
    return [sentence for sentence in sentences if len(sentence) >= 20]


def _extract_metric_phrase(text: str, patterns: list[str], max_len: int = 120) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            continue
        value = match.group(1).strip(" .:-")
        return value[:max_len]
    return None


def _extract_pricing_signals(text: str, state: ReviewEngineState) -> list[str]:
    candidates = list(state.get("pricing_signals") or [])
    for sentence in _split_sentences(text):
        lowered = sentence.lower()
        if any(hint in lowered for hint in PRICING_HINTS) and any(ch.isdigit() for ch in sentence):
            candidates.append(sentence)
    return _unique_keep_order(candidates)[:5]


def _extract_revenue_model(text: str) -> list[str]:
    lowered = text.lower()
    matches = [label for needle, label in REVENUE_MODEL_PATTERNS if needle in lowered]
    return _unique_keep_order(matches)[:4]


def _normalize_runway_months(raw: str | None) -> float | None:
    if not raw:
        return None

    month_match = re.search(r"(\d+(?:[\.,]\d+)?)\s*(?:bulan|months?)", raw, re.IGNORECASE)
    if month_match:
        return float(month_match.group(1).replace(",", "."))

    year_match = re.search(r"(\d+(?:[\.,]\d+)?)\s*(?:tahun|years?)", raw, re.IGNORECASE)
    if year_match:
        return round(float(year_match.group(1).replace(",", ".")) * 12, 2)

    return None


def _parse_money_to_number(raw: str | None) -> float | None:
    if not raw:
        return None

    money_match = re.search(
        r"(?:(?:rp|idr|usd|\$)\s*)?([\d\.,]+)\s*(juta|miliar|triliun|million|billion)?",
        raw,
        re.IGNORECASE,
    )
    if not money_match:
        return None

    number_text = money_match.group(1)
    suffix = (money_match.group(2) or "").lower()

    if "," in number_text and "." in number_text:
        if number_text.rfind(",") > number_text.rfind("."):
            number_text = number_text.replace(".", "").replace(",", ".")
        else:
            number_text = number_text.replace(",", "")
    elif number_text.count(".") > 1:
        number_text = number_text.replace(".", "")
    elif "." in number_text and "," not in number_text:
        left, right = number_text.split(".", 1)
        if right.isdigit() and len(right) == 3:
            number_text = left + right
    elif "," in number_text and "." not in number_text:
        number_text = number_text.replace(".", "").replace(",", ".")
    else:
        number_text = number_text.replace(",", "")

    try:
        value = float(number_text)
    except ValueError:
        return None

    multipliers = {
        "juta": 1_000_000,
        "miliar": 1_000_000_000,
        "triliun": 1_000_000_000_000,
        "million": 1_000_000,
        "billion": 1_000_000_000,
    }
    return value * multipliers.get(suffix, 1)


async def bizplan_financials_node(state: ReviewEngineState) -> dict:
    """
    Ekstraksi metrik finansial dari business plan.

    Output:
    - pricing, revenue_model
    - financial_metrics
    - burn_rate, runway_months, break_even_timeline
    - unit_economics_signals, financial_red_flags
    """
    analysis_id = state.get("analysis_id", "unknown")
    raw_markdown = state.get("raw_markdown") or ""
    document_tail = state.get("document_tail") or ""
    text = f"{raw_markdown[:7000]}\n\n{document_tail}".strip()

    print("\n[bizplan_financials] Memulai ekstraksi metrik finansial...")
    _safe_log(analysis_id, "bizplan_financials", "processing", "Menganalisis metrik finansial business plan...")

    if not text:
        _safe_log(analysis_id, "bizplan_financials", "done", "Metrik finansial: skip (dokumen kosong)")
        return {
            "revenue_model": [],
            "pricing": [],
            "financial_metrics": {},
            "burn_rate": None,
            "runway_months": None,
            "break_even_timeline": None,
            "unit_economics_signals": {},
            "financial_red_flags": [
                "Dokumen belum memuat informasi finansial yang bisa diekstrak.",
            ],
        }

    pricing = _extract_pricing_signals(text, state)
    revenue_model = _extract_revenue_model(text)

    cac = _extract_metric_phrase(
        text,
        [
            r"(?:cac|customer acquisition cost|biaya akuisisi pelanggan)\s*[:=\-]?\s*((?:rp|idr|usd|\$)?\s?[\d\.,]+(?:\s?(?:juta|miliar|triliun|million|billion))?)",
        ],
    )
    ltv = _extract_metric_phrase(
        text,
        [
            r"(?:ltv|clv|customer lifetime value|lifetime value)\s*[:=\-]?\s*((?:rp|idr|usd|\$)?\s?[\d\.,]+(?:\s?(?:juta|miliar|triliun|million|billion))?)",
        ],
    )
    gross_margin = _extract_metric_phrase(
        text,
        [
            r"(?:gross margin|margin kotor)\s*[:=\-]?\s*([\d\.,]+\s?%)",
        ],
    )
    burn_rate = _extract_metric_phrase(
        text,
        [
            r"(?:burn rate|monthly burn|cash burn|pembakaran kas)\s*[:=\-]?\s*((?:rp|idr|usd|\$)?\s?[\d\.,]+(?:\s?(?:juta|miliar|triliun|million|billion))?(?:\s*(?:per|/)\s*(?:bulan|month))?)",
        ],
    )
    runway_raw = _extract_metric_phrase(
        text,
        [
            r"(?:runway|cash runway)\s*[:=\-]?\s*([\d\.,]+\s*(?:bulan|months?|tahun|years?))",
            r"(?:bertahan selama|mencukupi untuk)\s+([\d\.,]+\s*(?:bulan|months?|tahun|years?))",
        ],
    )
    break_even_timeline = _extract_metric_phrase(
        text,
        [
            r"(?:break[- ]even|break even point|bep|titik impas)\s*[:=\-]?\s*([^\n\.]{3,120})",
            r"(?:mencapai titik impas dalam)\s+([^\n\.]{3,120})",
        ],
    )
    funding_needed = state.get("funding_ask")

    runway_months = _normalize_runway_months(runway_raw)

    cac_value = _parse_money_to_number(cac)
    ltv_value = _parse_money_to_number(ltv)
    ltv_cac_ratio = round(ltv_value / cac_value, 2) if cac_value and ltv_value and cac_value > 0 else None

    financial_metrics = {
        "pricing": pricing,
        "revenue_model": revenue_model,
        "cac": cac,
        "ltv": ltv,
        "gross_margin": gross_margin,
        "burn_rate": burn_rate,
        "runway_months": runway_months,
        "break_even_timeline": break_even_timeline,
        "funding_needed": funding_needed,
    }
    unit_economics_signals = {
        "cac": cac,
        "ltv": ltv,
        "ltv_cac_ratio": ltv_cac_ratio,
    }

    financial_red_flags: list[str] = []
    if not revenue_model:
        financial_red_flags.append("Model pendapatan belum tergambar jelas.")
    if not pricing:
        financial_red_flags.append("Strategi harga belum dijelaskan dengan angka yang jelas.")
    if not cac:
        financial_red_flags.append("CAC belum dicantumkan.")
    if not ltv:
        financial_red_flags.append("LTV belum dicantumkan.")
    if not burn_rate:
        financial_red_flags.append("Burn rate belum dicantumkan.")
    if runway_months is None:
        financial_red_flags.append("Runway belum dapat diestimasi.")
    if not break_even_timeline:
        financial_red_flags.append("Asumsi break-even belum dijelaskan.")

    print(f"[bizplan_financials] Revenue model: {revenue_model}")
    print(f"[bizplan_financials] Pricing signals: {len(pricing)} | Red flags: {len(financial_red_flags)}")
    print(f"[bizplan_financials] CAC: {cac or 'N/A'} | LTV: {ltv or 'N/A'} | Runway: {runway_months or 'N/A'}")

    _safe_log(
        analysis_id,
        "bizplan_financials",
        "done",
        f"Metrik finansial siap - red flags: {len(financial_red_flags)}",
    )

    return {
        "revenue_model": revenue_model,
        "pricing": pricing,
        "financial_metrics": financial_metrics,
        "burn_rate": burn_rate,
        "runway_months": runway_months,
        "break_even_timeline": break_even_timeline,
        "unit_economics_signals": unit_economics_signals,
        "financial_red_flags": financial_red_flags,
    }
