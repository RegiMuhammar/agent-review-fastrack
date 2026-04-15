from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)

def test_evaluate_endpoint_missing_header():
    """Test endpoint tanpa header internal key harusnya ditolak."""
    response = client.post(
        "/api-agent/evaluate",
        json={
            "analysis_id": "test-1",
            "file_url": "http://localhost:8000/test.pdf",
            "doc_type": "essay"
        }
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Unauthorized Bro"}

def test_evaluate_endpoint_success():
    """Test endpoint dengan schema yang benar."""
    response = client.post(
        "/api-agent/evaluate",
        headers={"X-Internal-Key": settings.INTERNAL_KEY},
        json={
            "analysis_id": "test-1",
            "file_url": "http://localhost:8000/test.pdf",
            "doc_type": "essay"
        }
    )
    
    # Endpoint menggunakan BackgroundTasks, jadi dia langsung return "queued"
    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data
    assert data["status"] == "queued"

def test_evaluate_endpoint_invalid_schema():
    """Test endpoint kurang data doc_type yang diwajibkan."""
    response = client.post(
        "/api-agent/evaluate",
        headers={"X-Internal-Key": settings.INTERNAL_KEY},
        json={
            "analysis_id": "test-1",
            "file_url": "http://localhost:8000/test.pdf",
            # doc_type sengaja dihilangkan
        }
    )
    assert response.status_code == 422 # Unprocessable Entity (Pydantic validation error)
