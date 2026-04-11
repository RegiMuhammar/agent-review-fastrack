from fastapi import Request, HTTPException

from app.core.config import settings

async def verify_internal_key(request: Request):
    internal_key = request.headers.get("X-Internal-Key")
    if internal_key != settings.INTERNAL_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized Bro")