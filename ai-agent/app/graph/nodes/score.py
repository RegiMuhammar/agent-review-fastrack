import json
import re

from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from app.prompts.essay import ESSAY_SYSTEM_PROMPT
from app.prompts.research import RESEARCH_SYSTEM_PROMPT
from app.core.config import settings
from app.graph.state import ReviewEngineState

DIMENSION_WEIGHTS = {
    "essay": {
        "thesis_clarity": 0.20,
        "argument_coherence": 0.25,
        "evidence_quality": 0.20,
        "structure_organization": 0.15,
        "writing_style_clarity": 0.10,
        "citation_integrity": 0.10,
    },
    "research": {
        "novelty": 0.25, "signifikansi": 0.20,
        "metodologi": 0.20, "kejelasan": 0.15,
        "prior_work": 0.10, "kontribusi": 0.10,
    },
    "bizplan": {
        "problem_solution": 0.25, "market_size": 0.20,
        "business_model": 0.20, "competitive": 0.15,
        "team": 0.10, "financial": 0.10,
    },
}

# Instruksi tambahan per doc_type
CONTEXT_INSTRUCTIONS = {
    "essay": (
        "Gunakan dimensi evaluasi yang sesuai untuk tipe dokumen: essay.\n"
        "Pastikan output murni text berformat JSON yang valid. "
        "Jangan gunakan markdown code block (seperti ```json ... ```)."
    ),
    "research": (
        "Gunakan dimensi evaluasi yang sesuai untuk tipe dokumen: research paper.\n"
        "Context yang diberikan sudah mencakup:\n"
        "- Metadata paper (title, abstract, keywords, domain)\n"
        "- Evidence dari section-section utama dokumen (introduction, method, results, conclusion)\n"
        "- Referensi relevan dari literatur terkait\n\n"
        "Instruksi khusus untuk scoring research:\n"
        "- Evaluasi secara TEMPORAL: Perhatikan tahun publikasi di metadata. Jangan gunakan standar 2024 untuk paper lama.\n"
        "- Evaluasi NOVELTY berdasarkan kebaruan dibanding literatur yang tersedia SAAT TAHUN PUBLIKASI.\n"
        "- Evaluasi SIGNIFIKANSI berdasarkan dampak jangka panjang (foundational landmark) jika paper sudah berumur.\n"
        "- Evaluasi PRIOR WORK dengan melihat apakah paper menyitasi/membahas literatur yang cukup sesuai zamannya.\n"
        "- Evaluasi METODOLOGI berdasarkan evidence dari section method.\n"
        "- Evaluasi KONTRIBUSI berdasarkan klaim di conclusion vs evidence di results.\n\n"
        "Pastikan output murni text berformat JSON yang valid. "
        "Jangan gunakan markdown code block (seperti ```json ... ```)."
    ),
    "bizplan": (
        "Gunakan dimensi evaluasi yang sesuai untuk tipe dokumen: business plan.\n"
        "Pastikan output murni text berformat JSON yang valid. "
        "Jangan gunakan markdown code block (seperti ```json ... ```)."
    ),
}


def _safe_log(analysis_id: str, step: str, status: str, message: str) -> None:
    """Helper untuk logging progres ke Laravel secara aman."""
    try:
        import asyncio
        from app.services.laravel_client import log_step
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(log_step(analysis_id, step, status, message))
        except RuntimeError:
            asyncio.run(log_step(analysis_id, step, status, message))
    except Exception as exc:
        print(f"[score_node][log_step] log gagal: {exc}")


def _clean_llm_json(raw: str) -> str:
    """Bersihkan output LLM dari markdown fences."""
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return raw.strip()


def _select_context(state: ReviewEngineState) -> tuple[str, str]:
    """
    Pilih context terbaik yang tersedia.
    
    Prioritas:
    1. review_context (Fungsi akhir dari research_agent atau essay_agent)
    2. agent_context (fallback default)
    
    Return: (context_text, source_label)
    """
    doc_type = state.get("doc_type", "essay")

    # Research & Essay: prioritaskan review_context jika tersedia
    if doc_type in ["research", "essay"]:
        review_context = state.get("review_context") or ""
        if review_context:
            return review_context, f"review_context ({doc_type}_agent)"

    # Essay/bizplan atau fallback: gunakan agent_context
    agent_context = state.get("agent_context") or ""
    if agent_context:
        return agent_context, "agent_context"

    # Last resort: raw_markdown slice
    raw = state.get("raw_markdown") or ""
    return raw[:6000], "raw_markdown (fallback)"


async def score_node(state: ReviewEngineState) -> dict:
    """
    LLM evaluate per dimensi + weighted scoring.
    
    Fase 8: 
    - Research path menggunakan review_context (metadata + evidence + refs)
    - Essay path tetap menggunakan agent_context (raw_markdown[:6000])
    - Prompt research diperkaya dengan instruksi reference-aware scoring
    """
    analysis_id = state["analysis_id"]
    doc_type = state["doc_type"]
    
    # 1. Update status
    print(f"\n[score_node] Memulai evaluasi dokumen: {doc_type}...")
    _safe_log(analysis_id, "scoring", "processing", "Mengevaluasi dokumen dan memberikan skor...")
    
    # 2. Pilih system prompt yang sesuai dengan tipe dokumen
    prompt_map = {
        "essay": ESSAY_SYSTEM_PROMPT,
        "research": RESEARCH_SYSTEM_PROMPT,
        # "bizplan": BIZPLAN_SYSTEM_PROMPT,
    }
    
    system_prompt = prompt_map.get(doc_type, ESSAY_SYSTEM_PROMPT)
    
    # 3. Pilih context terbaik (Fase 8: review_context untuk research)
    context_text, context_source = _select_context(state)
    print(f"[score_node] Context source: {context_source} ({len(context_text)} chars)")
    
    # Inisialisasi LLM
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.3,
        api_key=settings.GROQ_API_KEY
    )
    
    # 4. Bangun pesan context dengan instruksi spesifik
    instructions = CONTEXT_INSTRUCTIONS.get(doc_type, CONTEXT_INSTRUCTIONS["essay"])
    
    context_message = f"""DOKUMEN YANG DIEVALUASI:
{context_text}

INSTRUKSI:
{instructions}
"""
    
    print("[score_node] Memanggil LLM untuk evaluasi...")
    # 5. Panggil LLM
    try:
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=context_message)
        ])
        
        # Parse hasil
        raw_result = _clean_llm_json(response.content)
        result = json.loads(raw_result)
        
    except json.JSONDecodeError as exc:
        err_msg = f"Gagal membaca format JSON dari output LLM: {exc}"
        print(f"[score_node] ERROR: {err_msg}")
        _safe_log(analysis_id, "scoring", "error", err_msg)
        return {"error": err_msg, "is_valid": False}
    except Exception as exc:
        err_msg = f"Error saat memanggil LLM: {exc}"
        print(f"[score_node] ERROR: {err_msg}")
        _safe_log(analysis_id, "scoring", "error", err_msg)
        return {"error": err_msg, "is_valid": False}

    # 6. Hitung Overall Score (Weighted Average)
    weights = DIMENSION_WEIGHTS.get(doc_type, DIMENSION_WEIGHTS["essay"])
    
    dimension_scores = {}
    for dim in result.get("dimensions", []):
        key = dim.get("key")
        score = float(dim.get("score", 0))
        dimension_scores[key] = score
        
    # Perhitungan weighted score
    score_overall = sum(
        dimension_scores.get(key, 0) * weight
        for key, weight in weights.items()
    )
    
    # Pembulatan skor biar rapi
    score_overall = round(score_overall, 2)
    
    success_msg = f"Evaluasi selesai — Skor: {score_overall}/10 (context: {context_source})"
    print(f"[score_node] {success_msg}")
    _safe_log(analysis_id, "scoring", "done", success_msg)
    
    # 7. Return values untuk ditulis ke State
    return {
        "dimension_scores": dimension_scores,
        "score_overall": score_overall,
        "dimensions_feedback": result.get("dimensions", []),
        "overall_feedback": result.get("overall_feedback", ""),
        "summary": result.get("summary", ""),
        "is_valid": True,
        "error": None
    }

