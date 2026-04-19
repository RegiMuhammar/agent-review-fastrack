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

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from app.graph.state import ReviewEngineState
from app.core.config import settings

logger = logging.getLogger(__name__)

# Berapa referensi teratas yang masuk ke context LLM
TOP_K = 5

# Threshold minimal untuk masuk top_references
MIN_RELEVANCE_THRESHOLD = 0.3

# ── HEURISTIC SCORING ────────────────────────────────────────────────────────

def _normalize(text: str) -> set[str]:
    """Normalize teks ke set of lowercase words."""
    return set(re.sub(r"[^\w\s]", "", text.lower()).split())


def _heuristic_score(result: dict, paper_words: set[str], paper_keywords: list[str]) -> float:
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

    # 3. Recency
    year = result.get("year")
    if year and isinstance(year, int):
        if year >= 2023:
            recency = 1.0
        elif year >= 2020:
            recency = 0.7
        elif year >= 2015:
            recency = 0.4
        else:
            recency = 0.2
    else:
        recency = 0.5  # unknown year → neutral

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


async def _llm_rerank(candidates: list[dict], state: ReviewEngineState) -> list[dict] | None:
    """
    LLM rerank untuk kandidat teratas. Return None jika gagal.
    """
    title = state.get("title") or ""
    abstract = state.get("abstract") or ""
    domain = state.get("domain") or "general"

    # Build compact list
    results_text = "\n".join(
        f"[{i}] Title: {r['title']}\n"
        f"    Source: {r['source']} | Year: {r.get('year', 'N/A')}\n"
        f"    Snippet: {r['snippet'][:200]}"
        for i, r in enumerate(candidates)
    )

    user_content = (
        f"Paper Target:\nTitle: {title}\nDomain: {domain}\n"
        f"Abstract: {abstract[:600]}\n\n"
        f"Hasil Pencarian untuk Di-ranking:\n{results_text}"
    )

    try:
        llm = ChatGroq(
            model="llama-3.1-8b-instant",
            temperature=0,
            api_key=settings.GROQ_API_KEY,
        )

        response = await llm.ainvoke([
            SystemMessage(content=RERANK_SYSTEM_PROMPT),
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
    paper_words = _normalize(paper_title + " " + " ".join(paper_keywords))

    scored = []
    for r in search_results:
        h_score = _heuristic_score(r, paper_words, paper_keywords)
        scored.append({**r, "relevance_score": h_score})

    # Sort descending
    scored.sort(key=lambda x: x["relevance_score"], reverse=True)

    print(f"[search_rank] Heuristic scoring selesai:")
    for i, r in enumerate(scored[:5]):
        print(f"  #{i+1} [{r['relevance_score']:.3f}] {r['title'][:60]}")

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
    top_references = [
        r for r in ranked_results[:TOP_K]
        if r["relevance_score"] >= MIN_RELEVANCE_THRESHOLD
    ]

    summary = f"Ranking selesai — {len(top_references)} referensi terpilih dari {len(ranked_results)}"
    print(f"[search_rank] {summary}")
    if top_references:
        print(f"[search_rank] Top referensi:")
        for i, r in enumerate(top_references):
            print(f"  #{i+1} [{r['relevance_score']:.3f}] [{r['source']}] {r['title'][:60]}")

    _safe_log(analysis_id, "ranking", "done", summary)

    return {
        "ranked_results": ranked_results,
        "top_references": top_references,
    }
