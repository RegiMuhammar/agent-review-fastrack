import httpx
from app.core.config import settings

async def log_step(analysis_id: str, step: str, status: str, message: str):
    """Kirim progress log ke Laravel."""
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{settings.LARAVEL_URL}/api/v1/internal/analysis/log",
                headers={"X-Internal-Key": settings.INTERNAL_KEY},
                json={
                    "analysis_id": analysis_id,
                    "step": step,
                    "status": status,
                    "message": message,
                },
                timeout=10.0,
            )
    except Exception as e:
        print(f"[WARNING] [Laravel Client] Gagal mengirim log '{step}': {str(e)}")

async def send_callback(analysis_id: str, status: str, result: dict | None = None, error: str | None = None):
    """Kirim final result ke Laravel."""
    payload = {"analysis_id": analysis_id, "status": status}
    if result:
        payload["result"] = result
    if error:
        payload["error_message"] = error
    
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{settings.LARAVEL_URL}/api/v1/internal/analysis/callback",
                headers={"X-Internal-Key": settings.INTERNAL_KEY},
                json=payload,
                timeout=30.0,
            )
    except Exception as e:
        print(f"[WARNING] [Laravel Client] Gagal mengirim callback akhir: {str(e)}")