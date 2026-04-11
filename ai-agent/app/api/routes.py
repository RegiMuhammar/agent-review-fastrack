import uuid
from fastapi import APIRouter, Depends, BackgroundTasks

from app.api.schemas import EvaluateRequest, EvaluateResponse
from app.core.security import verify_internal_key

router = APIRouter()

@router.post("/evaluate", response_model=EvaluateResponse, dependencies=[Depends(verify_internal_key)])
async def evaluate(request: EvaluateRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())

    # TODO Fase 2: Jalankan pipeline di background
    # background_tasks.add_task(run_pipeline, request, task_id)
        
    return EvaluateResponse(task_id=task_id, status="queued")
