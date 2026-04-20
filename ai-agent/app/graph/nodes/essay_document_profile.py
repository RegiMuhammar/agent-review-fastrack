import re

from app.services.laravel_client import log_step


def _count_matches(patterns: list[str], text: str, weight: int, cap: int) -> int:
    """Hitung sinyal regex secara terkontrol agar essay panjang tidak over-score."""
    total = 0
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        total += min(len(matches), cap) * weight
    return total


def _build_topic_phrase(state: dict) -> str:
    """Susun frase topik dari metadata yang tersedia."""
    title = (state.get("title") or "").strip()
    keywords = [kw.strip() for kw in (state.get("keywords") or []) if kw.strip()]
    abstract = (state.get("abstract") or "").strip()

    if title:
        return title[:120]
    if keywords:
        return " ".join(keywords[:4])[:120]
    if abstract:
        words = re.findall(r"[A-Za-z][A-Za-z\-]{3,}", abstract)
        return " ".join(words[:8])[:120] or "essay topic"
    return "essay topic"


def _build_essay_queries(state: dict, include_academic_sources: bool) -> dict[str, list[str]]:
    """Bangun query verifikasi fakta dan konteks umum untuk essay."""
    topic = _build_topic_phrase(state)
    keywords = [kw.strip() for kw in (state.get("keywords") or []) if kw.strip()]
    keyword_tail = " ".join(keywords[:3]).strip()
    scoped_topic = f"{topic} {keyword_tail}".strip()

    queries: dict[str, list[str]] = {
        "tavily": [
            f"{scoped_topic} fact check".strip(),
            f"{scoped_topic} statistics report".strip(),
            f"{scoped_topic} background analysis".strip(),
        ]
    }

    if include_academic_sources:
        academic_seed = scoped_topic or topic
        queries["semanticscholar"] = [
            academic_seed,
            f"{academic_seed} literature review".strip(),
        ]

    return queries


async def essay_document_profile_node(state: dict) -> dict:
    """
    Prepare context dan evaluasi heuristik web search untuk essay.
    Output tetap sama:
      - agent_context
      - search_queries
      - run_essay_web_search
    """

    analysis_id = state.get("analysis_id", "unknown")

    await log_step(
        analysis_id,
        "preparing",
        "processing",
        "Menyiapkan profil dan evaluasi essay..."
    )

    
    # -----------------------------------------
    # Siapkan Context awal
    # -----------------------------------------

    raw_md = state.get("raw_markdown", "")
    title = state.get("title", "")
    keywords = state.get("keywords", [])
    abstract = state.get("abstract", "")
    analysis_window = raw_md[:8000]
    agent_context = raw_md[:6000]

    # Heuristik Pencarian Web
    # Jika esai mengandung klaim argumen faktual, angka, atau indikator pengutipan yang kuat.
    run_essay_web_search = False
    
# -----------------------------------------
    # Basic Gate
    # -----------------------------------------

    is_long_enough = len(raw_md) > 900

    # sentence count untuk claim density
    sentences = re.split(r"[.!?]+", analysis_window)
    sentence_count = max(len([s for s in sentences if s.strip()]), 1)

    # -----------------------------------------
    # Weighted Factual Heuristics
    # -----------------------------------------

    score = 0

    strong_patterns = [
        r"\b(?:19|20)\d{2}\b",
        r"\b\d+(?:\.\d+)?%",
        r"\b\d+(?:\.\d+)?\s*(?:million|billion|trillion|juta|miliar|triliun)\b",
        r"http[s]?://",
        r"\([A-Za-z][A-Za-z\s\-]+,\s?(?:19|20)\d{2}\)",
        r"\[[0-9]{1,3}\]",
        r"\b(?:according to|reported by|statistics from|berdasarkan data|menurut data)\b",
    ]

    medium_patterns = [
        r"\b(?:research(?:ers)? found|research shows|study found|survei menunjukkan)\b",
        r"\b(?:data menunjukkan|penelitian menunjukkan|laporan menunjukkan)\b",
        r"\b(?:increase|decrease|causes|results in|led to|correlate[sd]? with)\b",
        r"\b(?:lebih mungkin|kurang mungkin|secara signifikan|signifikan)\b",
    ]

    weak_patterns = [
        r"\b(?:menurut|berdasarkan|diperkirakan|diduga)\b",
        r"\b(?:experts say|para ahli|pengamat)\b",
    ]

    strong_score = _count_matches(strong_patterns, analysis_window, weight=3, cap=2)
    medium_score = _count_matches(medium_patterns, analysis_window, weight=2, cap=2)
    weak_score = _count_matches(weak_patterns, analysis_window, weight=1, cap=2)
    metadata_score = 0
    if title:
        metadata_score += 1
    if keywords:
        metadata_score += 1
    if abstract:
        metadata_score += 1

    score = strong_score + medium_score + weak_score + metadata_score

    # -----------------------------------------
    # Claim Density
    # -----------------------------------------

    claim_density = score / sentence_count

    # -----------------------------------------
    # Final Decision
    # -----------------------------------------

    include_academic_sources = strong_score >= 3 or bool(re.search(r"\([A-Za-z][A-Za-z\s\-]+,\s?(?:19|20)\d{2}\)", analysis_window))

    if is_long_enough and (score >= 7 or claim_density >= 0.35):
        run_essay_web_search = True

        await log_step(
            analysis_id,
            "preparing",
            "processing",
            (
                f"Factual claims terdeteksi (score={score}, density={claim_density:.2f}, "
                f"strong={strong_score}, medium={medium_score}). Mengaktifkan Web Search."
            )
        )

    else:

        await log_step(
            analysis_id,
            "preparing",
            "processing",
            (
                f"Essay dominan reflektif (score={score}, density={claim_density:.2f}, "
                f"strong={strong_score}, medium={medium_score}). Skip pencarian web."
            )
        )

    # Generate basic search queries jika berniat mencari (dapat dikembangkan dengan LLM nantinya bila perlu, namun ini minimal)
    # Retrieval prep tetap akan memanfaatkan ini/fallback jika kita teruskan.
    search_queries = {}
    
    # Extract metadata/title ke state jika ditaruh secara manual:
    if run_essay_web_search:
        search_queries = _build_essay_queries(state, include_academic_sources=include_academic_sources)

    await log_step(
        analysis_id,
        "preparing",
        "done",
        "Konteks analisis esai siap"
    )

    return {
        "agent_context": agent_context,
        "search_queries": search_queries,
        "run_essay_web_search": run_essay_web_search
    }
