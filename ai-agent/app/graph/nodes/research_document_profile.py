"""
research_document_profile.py — Document Profile Node (Fase 3)
=====================================================
Node profiling khusus jalur research, berjalan setelah routing dan sebelum
research_agent. Mengklasifikasikan domain, subdomain, paper type, dan
retrieval focus dari metadata dokumen.

Output profiling ini akan digunakan oleh:
- research_agent (context yang lebih kaya)
- query generation (Fase 4 — query search lebih terarah)
- search ranking (Fase 6 — relevance scoring per domain)

Desain defensif:
- Hanya membaca title + abstract + keywords (hemat token, ~1500 char max).
- Fallback aman ke 'general' jika LLM gagal.
- Node ini tidak mengubah field state manapun selain profiling fields.

Flow: ... → metadata_extract → route("research") → research_document_profile → research_agent → ...
"""

import json
import re

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from app.graph.state import ReviewEngineState
from app.core.config import settings

# ── CONSTANTS ────────────────────────────────────────────────────────────────

KNOWN_DOMAINS = [
    "computer_science",
    "machine_learning",
    "medicine",
    "biology",
    "physics",
    "chemistry",
    "mathematics",
    "social_science",
    "economics",
    "psychology",
    "environmental_science",
    "engineering",
    "linguistics",
    "education",
    "law",
    "general",
]

KNOWN_PAPER_TYPES = [
    "empirical",       # Penelitian eksperimental/observasional
    "survey",          # Literature review / systematic review
    "method",          # Proposal metode/algoritma baru
    "case_study",      # Studi kasus spesifik
    "theoretical",     # Analisis teoritis/matematis
    "applied",         # Penerapan teknik ke domain tertentu
]

KNOWN_RETRIEVAL_FOCUS = [
    "prior_work",      # Riset sebelumnya yang terkait
    "benchmark",       # Dataset / metrik evaluasi
    "methodology",     # Pendekatan / teknik sejenis
    "application",     # Implementasi & use case
    "theory",          # Fondasi teori
]

PROFILE_SYSTEM_PROMPT = f"""Kamu adalah classifier dokumen akademik yang presisi.
Diberikan judul, abstrak, dan keywords sebuah paper, klasifikasikan ke dalam profil yang tepat.

Jawab HANYA dengan objek JSON valid — tanpa markdown fences, tanpa teks tambahan.

Domain yang tersedia: {', '.join(KNOWN_DOMAINS)}
Tipe paper yang tersedia: {', '.join(KNOWN_PAPER_TYPES)}
Fokus retrieval yang tersedia: {', '.join(KNOWN_RETRIEVAL_FOCUS)}

Struktur JSON:
{{
  "domain": "salah satu domain dari daftar di atas",
  "sub_domain": "sub-bidang spesifik (contoh: 'natural_language_processing', 'oncology', 'quantum_mechanics')",
  "paper_type": "salah satu tipe paper dari daftar di atas",
  "retrieval_focus": ["pilih 1-3 fokus retrieval yang paling relevan dari daftar di atas"],
  "reasoning": "satu kalimat penjelasan singkat klasifikasi"
}}

Aturan:
- Pilih domain yang paling spesifik dan cocok
- Jika tidak yakin, gunakan "general" untuk domain
- retrieval_focus harus berupa array 1-3 item
- Jangan mengarang domain/paper_type/retrieval_focus di luar daftar yang diberikan
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
        print(f"[research_document_profile][log_step] log gagal (diabaikan): {exc}")


def _clean_llm_json(raw: str) -> str:
    """Bersihkan output LLM dari markdown fences."""
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return raw.strip()


def _default_profile() -> dict:
    """Fallback profile jika klasifikasi gagal."""
    return {
        "domain": "general",
        "sub_domain": "general",
        "paper_type": "empirical",
        "retrieval_focus": ["prior_work"],
    }


# ── NODE UTAMA ───────────────────────────────────────────────────────────────

async def research_document_profile_node(state: ReviewEngineState) -> dict:
    """
    LangGraph node: Klasifikasi profil dokumen research.

    Input dari state:
        - title, abstract, keywords (dari metadata_extract)
        - analysis_id (untuk logging)

    Output (di-merge ke state):
        - domain          : domain akademik utama
        - sub_domain      : sub-bidang spesifik
        - paper_type      : jenis paper (empirical/survey/method/dll)
        - retrieval_focus : list fokus retrieval untuk query generation
    """
    analysis_id = state.get("analysis_id", "unknown")
    title = state.get("title") or ""
    abstract = state.get("abstract") or ""
    keywords = state.get("keywords") or []

    print(f"\n[research_document_profile] Memulai profiling dokumen...")
    _safe_log(analysis_id, "profiling", "processing", "Menganalisis profil dokumen...")

    # ─── Guard: jika metadata terlalu minim, langsung fallback ───────────
    if not title and not abstract:
        print("[research_document_profile] WARNING: title & abstract kosong, skip profiling")
        _safe_log(analysis_id, "profiling", "done", "Profiling: skip (metadata kosong)")
        return _default_profile()

    # ─── LLM call untuk klasifikasi ──────────────────────────────────────
    llm = ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0,
        api_key=settings.GROQ_API_KEY,
    )

    # Kirim hanya metadata ringkas (hemat token)
    user_content = (
        f"Title: {title}\n\n"
        f"Abstract: {abstract[:1500]}\n\n"
        f"Keywords: {', '.join(keywords)}"
    )

    try:
        response = await llm.ainvoke([
            SystemMessage(content=PROFILE_SYSTEM_PROMPT),
            HumanMessage(content=user_content),
        ])

        cleaned = _clean_llm_json(response.content)
        data = json.loads(cleaned)

        # Parse & validasi fields
        domain = (data.get("domain") or "general").lower().replace(" ", "_")
        if domain not in KNOWN_DOMAINS:
            domain = "general"

        sub_domain = (data.get("sub_domain") or "general").strip()

        paper_type = (data.get("paper_type") or "empirical").lower().replace(" ", "_")
        if paper_type not in KNOWN_PAPER_TYPES:
            paper_type = "empirical"

        retrieval_focus_raw = data.get("retrieval_focus") or ["prior_work"]
        retrieval_focus = [
            rf for rf in retrieval_focus_raw
            if rf in KNOWN_RETRIEVAL_FOCUS
        ] or ["prior_work"]

        reasoning = data.get("reasoning", "")

        print(f"[research_document_profile] Domain: {domain}/{sub_domain}")
        print(f"[research_document_profile] Paper type: {paper_type}")
        print(f"[research_document_profile] Retrieval focus: {retrieval_focus}")
        if reasoning:
            print(f"[research_document_profile] Reasoning: {reasoning}")

        _safe_log(
            analysis_id, "profiling", "done",
            f"Profil: {domain}/{sub_domain} ({paper_type})",
        )

        return {
            "domain": domain,
            "sub_domain": sub_domain,
            "paper_type": paper_type,
            "retrieval_focus": retrieval_focus,
        }

    except json.JSONDecodeError as exc:
        print(f"[research_document_profile] WARNING: JSON parse gagal: {exc}")
        _safe_log(analysis_id, "profiling", "done", "Profiling: fallback (JSON error)")
        return _default_profile()

    except Exception as exc:
        print(f"[research_document_profile] WARNING: LLM call gagal: {exc}")
        _safe_log(analysis_id, "profiling", "done", "Profiling: fallback (error)")
        return _default_profile()
