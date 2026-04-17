import json
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from app.prompts.essay import ESSAY_SYSTEM_PROMPT
from app.prompts.research import RESEARCH_SYSTEM_PROMPT
from app.core.config import settings
from app.graph.state import ReviewEngineState

DIMENSION_WEIGHTS = {
    "essay": {
        "tesis_argumen": 0.25, 
        "struktur_koherensi": 0.20,
        "bukti_referensi": 0.20, 
        "gaya_bahasa": 0.15,
        "orisinalitas": 0.10, 
        "simpulan": 0.10,
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

async def score_node(state: ReviewEngineState) -> dict:
    """LLM evaluate per dimensi + weighted scoring."""
    analysis_id = state["analysis_id"]
    doc_type = state["doc_type"]
    
    # 1. Update status
    print(f"\n[score_node] Memulai evaluasi dokumen: {doc_type}...")
    _safe_log(analysis_id, "scoring", "processing", "Mengevaluasi dokumen dan memberikan skor...")
    
    # 2. Pilih system prompt yang sesuai dengan tipe dokumen
    prompt_map = {
        "essay": ESSAY_SYSTEM_PROMPT,
        "research": RESEARCH_SYSTEM_PROMPT,  # Fase 2: prompt khusus research
        # "bizplan": BIZPLAN_SYSTEM_PROMPT,  # Fase berikutnya
    }
    
    system_prompt = prompt_map.get(doc_type, ESSAY_SYSTEM_PROMPT)
    
    # Inisialisasi LLM model (OpenAI GPT-4o untuk evaluasi terbaik)
    # Pastikan OPENAI_API_KEY diset di .env
    llm = ChatGroq(
        model="llama-3.1-8b-instant", 
        temperature=0.3, # Temperature rendah agar output konsisten
        api_key=settings.GROQ_API_KEY
    )
    
    # 3. Siapkan konteks dari agent
    context_text = state.get("agent_context", "")
    
    context_message = f"""DOKUMEN YANG DIEVALUASI:
{context_text}

INSTRUKSI TAMBAHAN:
Gunakan dimensi evaluasi yang sesuai untuk tipe dokumen: {doc_type}. 
Pastikan output murni text berformat JSON yang valid. Jangan gunakan markdown code block (seperti ```json ... ```).
"""
    
    print("[score_node] Memanggil LLM untuk evaluasi...")
    # 4. Panggil LLM
    try:
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=context_message)
        ])
        
        # Parse hasil dari LLM
        # Kita perlu membersihkan output karena LLM seringkali mengembalikan JSON di dalam markdown code block
        raw_result = response.content.strip()
        if raw_result.startswith("```json"):
            raw_result = raw_result.replace("```json", "", 1)
        if raw_result.endswith("```"):
            raw_result = raw_result[:-3]
            
        result = json.loads(raw_result.strip())
        
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

    # 5. Hitung Overall Score (Weighted Average)
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
    
    success_msg = f"Evaluasi selesai — Skor: {score_overall}/10"
    print(f"[score_node] {success_msg}")
    _safe_log(analysis_id, "scoring", "done", success_msg)
    
    # 6. Return values untuk ditulis ke State
    return {
        "dimension_scores": dimension_scores,
        "score_overall": score_overall,
        "dimensions_feedback": result.get("dimensions", []),
        "overall_feedback": result.get("overall_feedback", ""),
        "summary": result.get("summary", ""),
        "is_valid": True,
        "error": None
    }
