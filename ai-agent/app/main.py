from fastapi import FastAPI
from app.api.routes import router


app = FastAPI(
    title="AI Review Engine - Agent Service Fastrack Edu",
    description="Langgraph-powered document review pipeline",
    version="0.0.1"
)

app.include_router(router, prefix="/api-agent")

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/health")
def health_check():
    return {"status": "OK ganteng!", "service": "ai-agent-review-working"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)