from pydantic import BaseModel

class EvaluateRequest(BaseModel):
    analysis_id: str
    file_path: str
    doc_type: str | None = None # hint dari user

class EvaluateResponse(BaseModel):
    task_id: str
    status: str = "queued"