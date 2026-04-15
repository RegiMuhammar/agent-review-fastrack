from typing import Literal
from pydantic import BaseModel

class EvaluateRequest(BaseModel):
    analysis_id: str
    doc_type: Literal["essay", "research", "bizplan"]
    file_url: str

class EvaluateResponse(BaseModel):
    task_id: str
    status: str = "queued"