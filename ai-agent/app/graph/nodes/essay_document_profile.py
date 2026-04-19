import re
from app.services.laravel_client import log_step


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
    agent_context = raw_md[:6000]

    # Heuristik Pencarian Web
    # Jika esai mengandung klaim argumen faktual, angka, atau indikator pengutipan yang kuat.
    run_essay_web_search = False
    
# -----------------------------------------
    # Basic Gate
    # -----------------------------------------

    is_long_enough = len(raw_md) > 1000

    # sentence count untuk claim density
    sentences = re.split(r"[.!?]+", agent_context)
    sentence_count = max(len([s for s in sentences if s.strip()]), 1)

    # -----------------------------------------
    # Weighted Factual Heuristics
    # -----------------------------------------

    score = 0

    strong_patterns = [
        r"\d{4}",                         # tahun
        r"\d+%",                          # persentase
        r"\d+\s(million|billion|trillion)",
        r"according to",
        r"researchers found",
        r"research shows",
        r"study found",
        r"reported by",
        r"statistics from",
        r"http[s]?://",
        r"\([A-Za-z]+,\s?\d{4}\)"         # (Smith, 2020)
    ]

    medium_patterns = [
        r"data menunjukkan",
        r"penelitian",
        r"fakta bahwa",
        r"more likely",
        r"less likely",
        r"increase[d]?",
        r"decrease[d]?",
        r"causes",
        r"results in",
        r"led to"
    ]

    weak_patterns = [
        r"menurut",
        r"berdasarkan"
    ]

    # strong signals
    for pattern in strong_patterns:
        if re.search(pattern, agent_context, re.IGNORECASE):
            score += 3

    # medium signals
    for pattern in medium_patterns:
        if re.search(pattern, agent_context, re.IGNORECASE):
            score += 2

    # weak signals
    for pattern in weak_patterns:
        if re.search(pattern, agent_context, re.IGNORECASE):
            score += 1

    # -----------------------------------------
    # Claim Density
    # -----------------------------------------

    claim_density = score / sentence_count

    # -----------------------------------------
    # Final Decision
    # -----------------------------------------

    if is_long_enough and (
        score >= 5
        or claim_density > 0.30
    ):
        run_essay_web_search = True

        await log_step(
            analysis_id,
            "preparing",
            "processing",
            f"Factual claims terdeteksi (score={score}, density={claim_density:.2f}). Mengaktifkan Web Search."
        )

    else:

        await log_step(
            analysis_id,
            "preparing",
            "processing",
            f"Essay dominan reflektif (score={score}, density={claim_density:.2f}). Skip pencarian web."
        )

    # Generate basic search queries jika berniat mencari (dapat dikembangkan dengan LLM nantinya bila perlu, namun ini minimal)
    # Retrieval prep tetap akan memanfaatkan ini/fallback jika kita teruskan.
    search_queries = {}
    
    # Extract metadata/title ke state jika ditaruh secara manual:
    title = state.get("title", "")
    if run_essay_web_search:
        # Fallback queries sederhana yang dipakai retrieval_prep jika dia terpanggil.
        base_term = title if title else "academic analysis"

        search_queries = {
            "tavily": [
                f"{base_term} facts summary",
                f"{base_term} academic context"
            ]
        }

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