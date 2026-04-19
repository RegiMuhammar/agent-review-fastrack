"""
retrieval_prep.py — Retrieval Preparation Node (Fase 4)
========================================================
Node query generation khusus jalur research.
Membangun search queries terstruktur dari metadata dan profil dokumen.

Query dibangun per sumber:
- semanticscholar: bahasa akademik formal, nama konsep lengkap
- arxiv: istilah teknis presisi, singkatan metode
- tavily: implementasi, benchmark, konteks umum

Input: title, abstract, keywords, domain, sub_domain, paper_type, retrieval_focus
Output: search_queries = {"semanticscholar": [...], "arxiv": [...], "tavily": [...]}

Search belum dijalankan di fase ini — hanya pembentukan query.

Flow: ... → research_document_profile → retrieval_prep → research_agent → ...
"""

import json
import re

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from app.graph.state import ReviewEngineState
from app.core.config import settings

# ── CONSTANTS ────────────────────────────────────────────────────────────────

QUERY_GEN_SYSTEM_PROMPT = """Kamu adalah ahli strategi pencarian literatur akademik.
Diberikan metadata dan profil sebuah paper, buat search query yang optimal untuk tiga mesin pencari berbeda.

Setiap mesin pencari punya kekuatan berbeda:
- semanticscholar: database akademik — gunakan bahasa akademik formal, nama konsep lengkap, nama penulis penting jika ada
- arxiv: server preprint — gunakan istilah teknis presisi, nama model, singkatan metode
- tavily: web search umum — gunakan istilah praktis, implementasi, benchmark, konteks terapan

Jawab HANYA dengan objek JSON valid (tanpa markdown fences, tanpa teks tambahan):
{
  "semanticscholar": ["query1", "query2", "query3"],
  "arxiv": ["query1", "query2", "query3"],
  "tavily": ["query1", "query2", "query3"]
}

Aturan:
- 3 query per mesin pencari, masing-masing maksimal 12 kata
- Buat query dari spesifik ke umum: judul spesifik → metode → broader context
- Gunakan sudut pandang berbeda: nama metode, masalah yang dipecahkan, perbandingan baseline, domain aplikasi
- Untuk arxiv/semanticscholar: utamakan terminologi teknis/akademik
- Untuk tavily: sertakan juga istilah praktis/implementasi
- Sesuaikan query berdasarkan retrieval_focus yang diberikan
"""


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
        print(f"[retrieval_prep][log_step] log gagal (diabaikan): {exc}")


def _clean_llm_json(raw: str) -> str:
    """Bersihkan output LLM dari markdown fences."""
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return raw.strip()


def _build_fallback_queries(state: ReviewEngineState) -> dict[str, list[str]]:
    """Fallback queries berdasarkan title dan domain jika LLM gagal."""
    title = (state.get("title") or "")[:80]
    domain = state.get("domain") or "general"
    sub_domain = state.get("sub_domain") or "general"
    keywords = state.get("keywords") or []

    # Query dasar dari title
    base_query = title if title else f"{domain} {sub_domain}"
    keyword_query = " ".join(keywords[:3]) if keywords else sub_domain

    return {
        "semanticscholar": [
            base_query,
            f"{sub_domain} state of the art",
            keyword_query,
        ],
        "arxiv": [
            base_query,
            f"{sub_domain} survey",
            keyword_query,
        ],
        "tavily": [
            base_query,
            f"{domain} research methods",
            f"{sub_domain} implementation",
        ],
    }


# ── NODE UTAMA ───────────────────────────────────────────────────────────────

async def retrieval_prep_node(state: ReviewEngineState) -> dict:
    """
    LangGraph node: Generate search queries dari metadata & profil dokumen.

    Input dari state:
        - title, abstract, keywords (dari metadata_extract)
        - domain, sub_domain, paper_type, retrieval_focus (dari research_document_profile)
        - analysis_id (untuk logging)

    Output (di-merge ke state):
        - search_queries : dict per source, masing-masing berisi list query
    """
    analysis_id = state.get("analysis_id", "unknown")
    title = state.get("title") or ""
    abstract = state.get("abstract") or ""
    keywords = state.get("keywords") or []
    domain = state.get("domain") or "general"
    sub_domain = state.get("sub_domain") or "general"
    paper_type = state.get("paper_type") or "empirical"
    retrieval_focus = state.get("retrieval_focus") or ["prior_work"]

    print(f"\n[retrieval_prep] Memulai generasi search queries...")
    _safe_log(analysis_id, "query_gen", "processing", "Membuat search queries...")

    doc_type = state.get("doc_type", "research")

    # ─── Guard: metadata terlalu minim → fallback ────────────────────────
    if not title and not abstract:
        print("[retrieval_prep] WARNING: title & abstract kosong, gunakan fallback queries")
        fallback = _build_fallback_queries(state)
        _safe_log(analysis_id, "query_gen", "done", "Queries: fallback (metadata kosong)")
        return {"search_queries": fallback}
        
    # ─── Guard: doc_type == essay ────────────────────────────────────────
    if doc_type == "essay":
        print("[retrieval_prep] doc_type=essay bypass LLM query gen, using profile queries if any")
        existing_queries = state.get("search_queries", {})
        if not existing_queries:
            # Jika belum ada dari profil, panggil fallback sederhana
            existing_queries = _build_fallback_queries(state)
        _safe_log(analysis_id, "query_gen", "done", "Queries: generated from essay heuristic fallback")
        return {"search_queries": existing_queries}

    # ─── LLM call untuk generate queries ─────────────────────────────────
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.3,   # Sedikit kreativitas untuk variasi query
        api_key=settings.GROQ_API_KEY,
    )

    user_content = (
        f"Paper Title: {title}\n"
        f"Domain: {domain} / {sub_domain}\n"
        f"Paper Type: {paper_type}\n"
        f"Retrieval Focus: {', '.join(retrieval_focus)}\n"
        f"Keywords: {', '.join(keywords)}\n\n"
        f"Abstract:\n{abstract[:1200]}"
    )

    try:
        response = await llm.ainvoke([
            SystemMessage(content=QUERY_GEN_SYSTEM_PROMPT),
            HumanMessage(content=user_content),
        ])

        cleaned = _clean_llm_json(response.content)
        data = json.loads(cleaned)

        # Parse & limit queries per source
        search_queries = {
            "semanticscholar": data.get("semanticscholar", [])[:3],
            "arxiv": data.get("arxiv", [])[:3],
            "tavily": data.get("tavily", [])[:3],
        }

        # Validasi minimal: pastikan ada query
        total = sum(len(v) for v in search_queries.values())
        if total == 0:
            raise ValueError("LLM mengembalikan 0 queries")

        print(f"[retrieval_prep] Queries generated:")
        for source, queries in search_queries.items():
            print(f"  [{source}] {queries}")

        _safe_log(
            analysis_id, "query_gen", "done",
            f"Queries: {total} total (SS:{len(search_queries['semanticscholar'])}, "
            f"arXiv:{len(search_queries['arxiv'])}, Tavily:{len(search_queries['tavily'])})",
        )

        return {"search_queries": search_queries}

    except json.JSONDecodeError as exc:
        print(f"[retrieval_prep] WARNING: JSON parse gagal: {exc}")
        fallback = _build_fallback_queries(state)
        _safe_log(analysis_id, "query_gen", "done", "Queries: fallback (JSON error)")
        return {"search_queries": fallback}

    except Exception as exc:
        print(f"[retrieval_prep] WARNING: LLM call gagal: {exc}")
        fallback = _build_fallback_queries(state)
        _safe_log(analysis_id, "query_gen", "done", "Queries: fallback (error)")
        return {"search_queries": fallback}
