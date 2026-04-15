import uuid
from fastapi import APIRouter, Depends, BackgroundTasks

from app.api.schemas import EvaluateRequest, EvaluateResponse
from app.core.security import verify_internal_key
from app.graph.builder import review_pipeline
from app.services.laravel_client import send_callback

router = APIRouter()

async def run_pipeline(request: EvaluateRequest, task_id: str):
    """Jalankan LangGraph pipeline di background"""
    try:
        initial_state = {
            "analysis_id" : request.analysis_id,
            "file_url" : request.file_url,
            "doc_type": request.doc_type,
        }

        # Panggil pipeline
        result = await review_pipeline.ainvoke(initial_state)
        final_data = result.get("final_result")
        
        # Cetak hasil ke terminal agar bisa dilihat saat testing lokal!
        import json
        print("\n\n" + "="*50)
        print("🎉 HASIL AKHIR EVALUASI AI:")
        print(json.dumps(final_data, indent=2))
        print("="*50 + "\n\n")

        # Kirim result ke Laravel
        await send_callback(
            analysis_id=request.analysis_id,
            status="done",
            result=final_data,
        )

    except Exception as e:
        # Kirim error ke Laravel
        await send_callback(
            analysis_id=request.analysis_id,
            status="failed pipeline",
            error=str(e),
        )

@router.post("/evaluate", response_model=EvaluateResponse, dependencies=[Depends(verify_internal_key)])
async def evaluate(request: EvaluateRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())

    #  Jalankan pipeline di background
    background_tasks.add_task(run_pipeline, request, task_id)
        
    return EvaluateResponse(task_id=task_id, status="queued")
