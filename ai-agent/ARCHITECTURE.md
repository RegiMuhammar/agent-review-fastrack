# 🧠 AI Agent — Architecture & Step-by-Step Roadmap

> Dokumen ini menjelaskan arsitektur lengkap folder `ai-agent`, cara memulai development dari nol,
> roadmap menuju MVP, dan pathway ke production-ready.
> 
> **Reference**: [technical-implementation.md](../technical-implementation.md) — Sub 9: AI Agent Architecture

---

## 📋 Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Folder Structure Explained](#2-folder-structure-explained)
3. [LangGraph Pipeline Deep Dive](#3-langgraph-pipeline-deep-dive)
4. [ReviewEngineState](#4-reviewenginestate)
5. [Communication Flow](#5-communication-flow-ai-agent--laravel)
6. [Step-by-Step: Fase 1 — Foundation (Setup & Boilerplate)](#6-fase-1--foundation-setup--boilerplate)
7. [Step-by-Step: Fase 2 — Core Pipeline (MVP)](#7-fase-2--core-pipeline-mvp)
8. [Step-by-Step: Fase 3 — Tools & Multi-Agent](#8-fase-3--tools--multi-agent)
9. [Step-by-Step: Fase 4 — Production Ready](#9-fase-4--production-ready)
10. [Dependency Map](#10-dependency-map)
11. [Environment Variables](#11-environment-variables)

---

## 1. Architecture Overview

AI Agent adalah **microservice FastAPI** yang menjalankan pipeline LangGraph untuk mengevaluasi dokumen. 
Service ini bersifat **stateless** — dia menerima request dari Laravel, memproses dokumen, lalu mengirim result kembali ke Laravel via callback.

```
┌─────────────────────────────────────────────────────────┐
│                      AI AGENT SERVICE                    │
│                                                          │
│  FastAPI Server (port 8001)                              │
│  ┌──────────────────────────────────────────────────┐    │
│  │              POST /evaluate                       │    │
│  │  Terima request dari Laravel Queue Worker        │    │
│  └───────────────────┬──────────────────────────────┘    │
│                      │                                   │
│                      ▼                                   │
│  ┌──────────────────────────────────────────────────┐    │
│  │           LangGraph Pipeline (async)              │    │
│  │                                                    │    │
│  │  extract → validate                               │    │
│  │      ↓ (conditional routing by doc_type input)    │    │
│  │  essay_agent / research_agent / bizplan_agent     │    │
│  │      ↓                                            │    │
│  │  tool_dispatcher → score → generate               │    │
│  └───────────────────┬──────────────────────────────┘    │
│                      │                                   │
│                      ▼                                   │
│  ┌──────────────────────────────────────────────────┐    │
│  │         Laravel Client (callback + logs)          │    │
│  │  POST /internal/analysis/callback  (result)      │    │
│  │  POST /internal/analysis/log       (progress)    │    │
│  └──────────────────────────────────────────────────┘    │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Prinsip Utama:**
- **Stateless** — tidak menyimpan data di database sendiri, semua result dikirim ke Laravel
- **Pure Python** — tidak ada coupling dengan PHP/Laravel internals
- **Async-first** — semua operasi I/O menggunakan `async/await`
- **Modular nodes** — setiap node LangGraph adalah fungsi Python independen

---

## 2. Folder Structure Explained

```
ai-agent/
├── app/                          # 🏗️ Source code utama
│   ├── api/                      # 🌐 HTTP Layer (FastAPI)
│   │   ├── __init__.py
│   │   ├── routes.py             # Endpoint POST /evaluate
│   │   └── schemas.py            # Pydantic models (request/response)
│   │
│   ├── graph/                    # 🧩 LangGraph Pipeline
│   │   ├── __init__.py
│   │   ├── state.py              # ReviewEngineState (TypedDict)
│   │   ├── builder.py            # Compile StateGraph + conditional edges
│   │   └── nodes/                # 🔧 Pipeline Nodes (setiap step)
│   │       ├── __init__.py
│   │       ├── extract.py        # PDF → Markdown (pymupdf4llm)
│   │       ├── essay_agent.py    # Persona: kritikus sastra
│   │       ├── research_agent.py # Persona: peer reviewer ICLR-standard
│   │       ├── bizplan_agent.py  # Persona: VC analyst
│   │       ├── tool_dispatcher.py# Orchestrate tool calls per doc_type
│   │       ├── score.py          # Weighted average scoring per dimensi
│   │       └── generate.py       # Assemble final JSON result
│   │
│   ├── tools/                    # 🔨 External Tool Integrations
│   │   ├── __init__.py
│   │   ├── web_search.py         # Tavily API — general web search
│   │   ├── citation_lookup.py    # arXiv API — academic citations
│   │   ├── rubric_retriever.py   # Load rubric markdown files
│   │   └── market_search.py      # Web search fokus market data
│   │
│   ├── prompts/                  # 📝 System Prompts per Doc Type
│   │   ├── __init__.py
│   │   ├── essay.py              # Prompt: reviewer essay akademik
│   │   ├── research.py           # Prompt: peer reviewer jurnal ilmiah
│   │   └── bizplan.py            # Prompt: VC/investor analyst
│   │
│   ├── services/                 # 🔗 External Service Clients
│   │   ├── __init__.py
│   │   ├── pdf_extractor.py      # Download PDF via endpoint internal Laravel + extract markdown
│   │   └── laravel_client.py     # HTTP client: callback + progress log
│   │
│   └── core/                     # ⚙️ App Configuration
│       ├── __init__.py
│       ├── config.py             # Pydantic Settings (.env loader)
│       └── security.py           # Validasi X-Internal-Key header
│
├── data/                         # 📊 Static Data Files
│   └── rubrics/                  # Rubrik evaluasi per doc_type
│       ├── essay_rubric.md
│       ├── research_rubric.md
│       └── bizplan_rubric.md
│
├── tests/                        # 🧪 Test Suite (tambahkan nanti)
│   ├── __init__.py
│   ├── test_extract.py
│   ├── test_graph.py
│   └── conftest.py
│
├── .env                          # Environment variables (JANGAN commit!)
├── .env.example                  # Template env vars
├── .gitignore
├── .python-version
├── main.py                       # 🚀 App entrypoint (uvicorn)
├── pyproject.toml
├── requirements.txt
└── ARCHITECTURE.md               # 📖 Dokumen ini
```

### Penjelasan Tiap Layer

| Layer | Folder | Fungsi | Kapan Dibuat |
|-------|--------|--------|-------------|
| **HTTP** | `app/api/` | Terima request, validasi input, return response | Fase 1 |
| **Pipeline** | `app/graph/` | Orkestrasi seluruh pipeline review AI | Fase 1-2 |
| **Nodes** | `app/graph/nodes/` | Setiap node = 1 step pipeline (extract, score, generate, dll) | Fase 2-3 |
| **Tools** | `app/tools/` | Integrasi external: search, citations, rubric | Fase 3 |
| **Prompts** | `app/prompts/` | System prompt untuk setiap persona reviewer | Fase 2 |
| **Services** | `app/services/` | Client untuk berkomunikasi dengan Laravel (callback, log, file endpoint) | Fase 1 |
| **Core** | `app/core/` | Config, env vars, security middleware | Fase 1 |
| **Data** | `data/rubrics/` | File rubrik statis (markdown) | Fase 2 |
| **Tests** | `tests/` | Unit & integration tests | Fase 3-4 |

---

## 3. LangGraph Pipeline Deep Dive

Pipeline ini adalah **StateGraph** dari LangGraph. Setiap node menerima `state`, memodifikasinya, dan mengembalikan perubahan.

```
START
  │
  ▼
┌─────────┐
│ extract  │  Download PDF dari Laravel API → Convert ke Markdown via pymupdf4llm
└────┬─────┘
     │
     ▼
┌──────────┐
│ validate │  Cek: minimal 2 halaman, panjang teks cukup, bahasa valid
└────┬─────┘
     │
     ├── is_valid = False → END (return error)
     │
     │ ◄── CONDITIONAL EDGE (routing berdasarkan doc_type dari input Laravel)
     │
     ├── "essay"    → ┌───────────────┐
     │                │ essay_agent   │  Siapkan context + search queries untuk essay
     │                └───────┬───────┘
     │                        │
     ├── "research" → ┌───────────────────┐
     │                │ research_agent    │  Siapkan context + search queries untuk paper
     │                └───────┬───────────┘
     │                        │
     └── "bizplan"  → ┌───────────────┐
                      │ bizplan_agent │  Siapkan context + search queries untuk bizplan
                      └───────┬───────┘
                              │
                              ▼
                      ┌──────────────────┐
                      │ tool_dispatcher  │  Jalankan tools berdasarkan doc_type:
                      │                  │  • Essay: web_search + rubric_retriever
                      │                  │  • Research: citation_lookup + web_search
                      │                  │  • Bizplan: market_search + web_search
                      └────────┬─────────┘
                               │
                               ▼
                      ┌────────┐
                      │ score  │  LLM evaluate per dimensi + weighted scoring
                      └───┬────┘
                          │
                          ▼
                      ┌──────────┐
                      │ generate │  Assemble semua data → final_result JSON
                      └────┬─────┘
                           │
                           ▼
                         END → POST callback ke Laravel
```

### Conditional Edge Logic

```python
def route_by_doc_type(state: ReviewEngineState) -> str:
    """doc_type sudah tersedia dari input Laravel (user pilih saat upload)."""
    if not state.get("is_valid", False):
        return "end_with_error"
    return state["doc_type"]  # "essay" | "research" | "bizplan"
```

---

## 4. ReviewEngineState

State adalah **satu-satunya data yang mengalir** melalui semua node. Setiap node membaca dan menulis ke state ini.

```python
class ReviewEngineState(TypedDict):
    # ── Input (dari Laravel — user memilih doc_type saat upload) ──
    analysis_id:   str              # ID dari tabel analysis
    file_url:      str              # URL endpoint internal Laravel untuk download PDF
    doc_type:      Literal["essay", "research", "bizplan"]  # Tipe dokumen (dipilih user)

    # ── Extraction ──
    raw_markdown:  str              # Hasil convert PDF → Markdown
    page_count:    int              # Jumlah halaman PDF
    title:         str | None       # Judul dokumen (jika terdeteksi)
    is_valid:      bool             # Lolos validasi atau tidak
    error:         str | None       # Pesan error jika gagal

    # ── Agent Preparation ──
    agent_context:   str            # Context yang disiapkan agent
    search_queries:  list[str]      # Query untuk external search

    # ── Tool Results ──
    tool_results: Annotated[list[dict], operator.add]  # Akumulasi dari semua tools

    # ── Scoring ──
    dimension_scores:     dict[str, float]    # Skor per dimensi
    score_overall:        float | None        # Skor akhir (weighted average)
    dimensions_feedback:  list[dict]          # Feedback narasi per dimensi
    overall_feedback:     str                 # Feedback keseluruhan
    summary:              str                 # Summary singkat

    # ── Final Output ──
    final_result: dict | None       # JSON lengkap untuk dikirim ke Laravel
```

---

## 5. Communication Flow (AI Agent ↔ Laravel)

### Inbound: Laravel → AI Agent

```
POST /evaluate
Headers:
  X-Internal-Key: {secret}
  Content-Type: application/json
Body:
  {
    "analysis_id": "123",
    "file_url": "http://localhost:8000/api/v1/internal/analysis/123/file",
    "doc_type": "essay"  // dipilih user saat upload (required)
  }
Response:
  {
    "task_id": "uuid-xxx",
    "status": "queued"
  }
```

### Outbound: AI Agent → Laravel (Progress Logging)

Setiap kali node selesai dieksekusi:

```
POST /api/v1/internal/analysis/log
Headers:
  X-Internal-Key: {secret}
Body:
  {
    "analysis_id": "123",
    "step": "extracting",      // extracting|preparing|searching|scoring|generating|done
    "status": "done",          // processing|done|failed
    "message": "Dokumen berhasil diekstrak (12 halaman)"
  }
```

### Outbound: AI Agent → Laravel (Final Callback)

Setelah pipeline selesai:

```
POST /api/v1/internal/analysis/callback
Headers:
  X-Internal-Key: {secret}
Body:
  {
    "analysis_id": "123",
    "status": "done",
    "result": { ... full result_json ... }
  }
```

---

## 6. Fase 1 — Foundation (Setup & Boilerplate)

> **Goal**: FastAPI bisa jalan, terima request, dan return response dummy.
> **Estimasi**: 1-2 hari

### Step 1.1 — Setup Environment & Dependencies

```bash
# Pastikan Python 3.11+ sudah terinstall
python --version

# Install dependencies via pip (atau uv)
pip install -r requirements.txt
```

Update `requirements.txt` menjadi:

```
fastapi
uvicorn[standard]
pydantic-settings
httpx
python-dotenv
python-multipart
pymupdf4llm
langgraph
langchain
langchain-openai
langchain-anthropic
tavily-python
```

### Step 1.2 — Buat Folder Structure

```bash
# Dari folder ai-agent/
mkdir -p app/api
mkdir -p app/graph/nodes
mkdir -p app/tools
mkdir -p app/prompts
mkdir -p app/services
mkdir -p app/core
mkdir -p data/rubrics
mkdir -p tests
```

Buat `__init__.py` di setiap folder:

```bash
# Buat __init__.py kosong di setiap package
touch app/__init__.py
touch app/api/__init__.py
touch app/graph/__init__.py
touch app/graph/nodes/__init__.py
touch app/tools/__init__.py
touch app/prompts/__init__.py
touch app/services/__init__.py
touch app/core/__init__.py
touch tests/__init__.py
```

### Step 1.3 — Config & Environment

**`app/core/config.py`** — Load settings dari `.env`

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Laravel Communication
    LARAVEL_URL: str = "http://localhost:8000"
    INTERNAL_KEY: str = "super-secret-internal-key"
    
    # LLM API Keys
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""  # Opsional
    TAVILY_API_KEY: str = ""
    
    # File retrieval
    # PDF diambil dari endpoint internal Laravel (local storage)

    # LangSmith (opsional tracing)
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_API_KEY: str = ""
    
    class Config:
        env_file = ".env"

settings = Settings()
```

**`.env.example`** — Template (copy ke `.env` dan isi nilainya)

```env
LARAVEL_URL=http://localhost:8000
INTERNAL_KEY=super-secret-internal-key-ganti-ini

OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...

LANGCHAIN_TRACING_V2=false
LANGCHAIN_API_KEY=
```

### Step 1.4 — Security Middleware

**`app/core/security.py`** — Validasi internal key

```python
from fastapi import Request, HTTPException

from app.core.config import settings

async def verify_internal_key(request: Request):
    key = request.headers.get("X-Internal-Key")
    if key != settings.INTERNAL_KEY:
        raise HTTPException(status_code=403, detail="Forbidden: Invalid internal key")
```

### Step 1.5 — API Schemas

**`app/api/schemas.py`** — Pydantic models

```python
from pydantic import BaseModel

class EvaluateRequest(BaseModel):
    analysis_id: str
    file_url: str
    doc_type: str | None = None  # hint dari user

class EvaluateResponse(BaseModel):
    task_id: str
    status: str = "queued"
```

### Step 1.6 — API Routes (Dummy)

**`app/api/routes.py`** — Endpoint POST /evaluate

```python
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
```

### Step 1.7 — Main Entrypoint

**`main.py`** — Entrypoint FastAPI app

```python
from fastapi import FastAPI
from app.api.routes import router

app = FastAPI(
    title="AI Review Engine — Agent Service",
    description="LangGraph-powered document review pipeline",
    version="0.1.0",
)

app.include_router(router, prefix="/api")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "ai-agent"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
```

### Step 1.8 — Laravel Client Service

**`app/services/laravel_client.py`** — HTTP client untuk callback & log

```python
import httpx
from app.core.config import settings

async def log_step(analysis_id: str, step: str, status: str, message: str):
    """Kirim progress log ke Laravel."""
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

async def send_callback(analysis_id: str, status: str, result: dict | None = None, error: str | None = None):
    """Kirim final result ke Laravel."""
    payload = {"analysis_id": analysis_id, "status": status}
    if result:
        payload["result"] = result
    if error:
        payload["error_message"] = error
    
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{settings.LARAVEL_URL}/api/v1/internal/analysis/callback",
            headers={"X-Internal-Key": settings.INTERNAL_KEY},
            json=payload,
            timeout=30.0,
        )
```

### ✅ Checkpoint Fase 1

Setelah semua step di atas:

```bash
# Jalankan server
python main.py

# Test health check
curl http://localhost:8001/health

# Test evaluate endpoint (harus return 403 tanpa key)
curl -X POST http://localhost:8001/api-agent/evaluate

# Test evaluate endpoint (dengan key, harus return 200)
curl -X POST http://localhost:8001/api-agent/evaluate \
  -H "X-Internal-Key: super-secret-internal-key-ganti-ini" \
  -H "Content-Type: application/json" \
  -d '{"analysis_id": "1", "file_url": "http://localhost:8000/api/v1/internal/analysis/1/file", "doc_type": "essay"}'
```

---

## 7. Fase 2 — Core Pipeline (MVP)

> **Goal**: Pipeline bisa extract PDF dan menghasilkan review sederhana untuk **satu doc_type** (mulai dari **essay**). `doc_type` diberikan langsung oleh user via Laravel.
> **Estimasi**: 3-5 hari

### Step 2.1 — ReviewEngineState

**`app/graph/state.py`**

```python
from __future__ import annotations
import operator
from typing import Annotated, Literal, TypedDict

class ReviewEngineState(TypedDict):
    # Input (dari Laravel — user memilih doc_type saat upload)
    analysis_id:   str
    file_url:      str
    doc_type:      Literal["essay", "research", "bizplan"]

    # Extraction
    raw_markdown:  str
    page_count:    int
    title:         str | None
    is_valid:      bool
    error:         str | None


    # Agent prep
    agent_context:   str
    search_queries:  list[str]

    # Tools
    tool_results: Annotated[list[dict], operator.add]

    # Scoring
    dimension_scores:     dict[str, float]
    score_overall:        float | None
    dimensions_feedback:  list[dict]
    overall_feedback:     str
    summary:              str

    # Final
    final_result: dict | None
```

### Step 2.2 — Node: Extract

**`app/graph/nodes/extract.py`**

```python
import pymupdf4llm
from app.services.laravel_client import log_step

async def extract_node(state: dict) -> dict:
    """Download PDF dan convert ke Markdown."""
    await log_step(state["analysis_id"], "extracting", "processing", "Membaca dan mengekstrak dokumen...")
    
    # TODO: Download file dari URL terlebih dahulu (gunakan httpx)
    # Untuk MVP, pastikan bisa download dari endpoint internal Laravel
    
    import httpx
    import tempfile
    
    # Download file (pseudocode)
    # with httpx.Client() as client:
    #     resp = client.get(state["file_url"])
    #     simpan_ke_tmp(resp)
    
    # md_text = pymupdf4llm.to_markdown(tmp_path)
    # doc = fitz.open(tmp_path)
    # page_count = len(doc)
    # doc.close()
    
    await log_step(state["analysis_id"], "extracting", "done", f"Dokumen berhasil diekstrak")
    
    return {
        "raw_markdown": "", # md_text
        "page_count": 0, # page_count
        "is_valid": True,  # akan di-validate di node berikutnya
    }
```

### Step 2.3 — Prompts (Mulai dari Essay)

**`app/prompts/essay.py`**

```python
ESSAY_SYSTEM_PROMPT = """Kamu adalah reviewer akademik berpengalaman yang ahli dalam mengevaluasi essay.
Kamu menilai secara kritis namun konstruktif, memberikan feedback yang actionable.

Evaluasi essay berdasarkan dimensi berikut:
1. Tesis & Argumen (25%) — Kejelasan posisi, kekuatan argumen
2. Struktur & Koherensi (20%) — Alur logis, transisi antar paragraf
3. Bukti & Referensi (20%) — Penggunaan data/sumber pendukung
4. Gaya Bahasa (15%) — Akademis, konsisten, bebas jargon berlebihan
5. Orisinalitas (10%) — Perspektif unik, kontribusi baru
6. Simpulan (10%) — Kekuatan kesimpulan, implikasi

Format output sebagai JSON:
{
  "dimensions": [
    {"key": "tesis_argumen", "name": "Tesis & Argumen", "score": 8.5, "weight": 0.25, "feedback": "..."},
    ...
  ],
  "overall_feedback": "...",
  "summary": "...",
  "strengths": ["...", "..."],
  "improvements": ["...", "..."]
}

Berikan skor 1-10 untuk setiap dimensi. Bersikap jujur dan kritis."""
```

### Step 2.5 — Node: Essay Agent (MVP agent pertama)

**`app/graph/nodes/essay_agent.py`**

```python
from app.services.laravel_client import log_step

async def essay_agent_node(state: dict) -> dict:
    """Prepare context dan search queries untuk essay review."""
    await log_step(state["analysis_id"], "preparing", "processing", "Menyiapkan analisis essay...")
    
    # Siapkan context dari dokumen
    agent_context = state["raw_markdown"][:6000]  # Batasi untuk context window
    
    # Generate search queries berdasarkan topik essay
    search_queries = []  # MVP: belum pakai external search
    
    await log_step(state["analysis_id"], "preparing", "done", "Konteks analisis siap")
    
    return {
        "agent_context": agent_context,
        "search_queries": search_queries,
    }
```

### Step 2.6 — Node: Score

**`app/graph/nodes/score.py`**

```python
import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from app.prompts.essay import ESSAY_SYSTEM_PROMPT
from app.services.laravel_client import log_step
from app.core.config import settings

DIMENSION_WEIGHTS = {
    "essay": {
        "tesis_argumen": 0.25, "struktur": 0.20,
        "bukti": 0.20, "gaya": 0.15,
        "orisinalitas": 0.10, "simpulan": 0.10,
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

async def score_node(state: dict) -> dict:
    """LLM evaluate per dimensi + weighted scoring."""
    await log_step(state["analysis_id"], "scoring", "processing", "Mengevaluasi dan memberi skor...")
    
    doc_type = state["doc_type"]
    
    # Pilih prompt sesuai doc_type
    prompt_map = {
        "essay": ESSAY_SYSTEM_PROMPT,
        # "research": RESEARCH_SYSTEM_PROMPT,  # Fase 3
        # "bizplan": BIZPLAN_SYSTEM_PROMPT,     # Fase 3
    }
    system_prompt = prompt_map.get(doc_type, ESSAY_SYSTEM_PROMPT)
    
    llm = ChatOpenAI(model="gpt-4o", temperature=0.3, api_key=settings.OPENAI_API_KEY)
    
    # Siapkan context
    context = f"""DOKUMEN YANG DIEVALUASI:
{state['agent_context']}

RUBRIK EVALUASI:
Gunakan dimensi yang sesuai untuk tipe dokumen: {doc_type}
"""
    
    response = await llm.ainvoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=context)
    ])
    
    result = json.loads(response.content)
    
    # Hitung score_overall dari weighted average
    weights = DIMENSION_WEIGHTS[doc_type]
    dimension_scores = {}
    for dim in result["dimensions"]:
        dimension_scores[dim["key"]] = dim["score"]
    
    score_overall = sum(
        dimension_scores.get(key, 0) * weight
        for key, weight in weights.items()
    )
    
    await log_step(state["analysis_id"], "scoring", "done", f"Evaluasi selesai — Skor: {score_overall:.1f}/10")
    
    return {
        "dimension_scores": dimension_scores,
        "score_overall": round(score_overall, 2),
        "dimensions_feedback": result["dimensions"],
        "overall_feedback": result["overall_feedback"],
        "summary": result["summary"],
    }
```

### Step 2.7 — Node: Generate

**`app/graph/nodes/generate.py`**

```python
from app.services.laravel_client import log_step

async def generate_node(state: dict) -> dict:
    """Assemble final result JSON."""
    await log_step(state["analysis_id"], "generating", "processing", "Menyusun laporan evaluasi...")
    
    final_result = {
        "analysis_id": state["analysis_id"],
        "doc_type": state["doc_type"],
        "score_overall": state["score_overall"],
        "summary": state["summary"],
        "dimensions": state["dimensions_feedback"],
        "overall_feedback": state["overall_feedback"],
        "strengths": [],      # Akan diisi dari scoring result
        "improvements": [],   # Akan diisi dari scoring result
        "references": [],     # Akan diisi saat tools aktif (Fase 3)
    }
    
    await log_step(state["analysis_id"], "generating", "done", "Laporan evaluasi berhasil disusun")
    
    return {"final_result": final_result}
```

### Step 2.7 — Graph Builder

**`app/graph/builder.py`**

```python
from langgraph.graph import StateGraph, END

from app.graph.state import ReviewEngineState
from app.graph.nodes.extract import extract_node
from app.graph.nodes.essay_agent import essay_agent_node
from app.graph.nodes.score import score_node
from app.graph.nodes.generate import generate_node

def route_by_doc_type(state: ReviewEngineState) -> str:
    """Conditional edge: route ke agent berdasarkan doc_type dari input Laravel."""
    if not state.get("is_valid", False):
        return "end_with_error"
    
    doc_type = state["doc_type"]  # Sudah pasti ada, required dari Laravel
    
    # MVP: hanya essay yang aktif
    route_map = {
        "essay": "essay_agent",
        "research": "essay_agent",    # Fallback ke essay dulu (Fase 3)
        "bizplan": "essay_agent",     # Fallback ke essay dulu (Fase 3)
    }
    return route_map.get(doc_type, "essay_agent")

def build_graph() -> StateGraph:
    """Compile LangGraph pipeline (menggunakan doc_type dari input Laravel)."""
    graph = StateGraph(ReviewEngineState)
    
    # Tambahkan nodes
    graph.add_node("extract", extract_node)
    graph.add_node("essay_agent", essay_agent_node)
    # graph.add_node("research_agent", research_agent_node)  # Fase 3
    # graph.add_node("bizplan_agent", bizplan_agent_node)     # Fase 3
    graph.add_node("score", score_node)
    graph.add_node("generate", generate_node)
    
    # Set entry point
    graph.set_entry_point("extract")
    
    # Conditional edge langsung setelah extract (doc_type dari input Laravel)
    graph.add_conditional_edges(
        "extract",
        route_by_doc_type,
        {
            "essay_agent": "essay_agent",
            # "research_agent": "research_agent",  # Fase 3
            # "bizplan_agent": "bizplan_agent",     # Fase 3
            "end_with_error": END,
        }
    )
    
    # Agent → Score → Generate
    graph.add_edge("essay_agent", "score")
    graph.add_edge("score", "generate")
    graph.add_edge("generate", END)
    
    return graph.compile()

# Singleton compiled graph
review_pipeline = build_graph()
```

### Step 2.8 — Integrate Pipeline ke Route

Update **`app/api/routes.py`**:

```python
import uuid
from fastapi import APIRouter, Depends, BackgroundTasks

from app.api.schemas import EvaluateRequest, EvaluateResponse
from app.core.security import verify_internal_key
from app.graph.builder import review_pipeline
from app.services.laravel_client import send_callback

router = APIRouter()

async def run_pipeline(request: EvaluateRequest, task_id: str):
    """Jalankan LangGraph pipeline di background."""
    try:
        initial_state = {
            "analysis_id": request.analysis_id,
            "file_url": request.file_url,
            "doc_type": request.doc_type,
        }
        
        result = await review_pipeline.ainvoke(initial_state)
        
        # Kirim result ke Laravel
        await send_callback(
            analysis_id=request.analysis_id,
            status="done",
            result=result.get("final_result"),
        )
        
    except Exception as e:
        # Kirim error ke Laravel
        await send_callback(
            analysis_id=request.analysis_id,
            status="failed",
            error=str(e),
        )

@router.post("/evaluate", response_model=EvaluateResponse, dependencies=[Depends(verify_internal_key)])
async def evaluate(request: EvaluateRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    
    # Jalankan pipeline di background
    background_tasks.add_task(run_pipeline, request, task_id)
    
    return EvaluateResponse(task_id=task_id, status="queued")
```

### ✅ Checkpoint Fase 2 (MVP)

Pada titik ini, kamu punya:

- ✅ FastAPI server dengan endpoint `/evaluate`yang di-protect
- ✅ LangGraph pipeline: extract → essay_agent → score → generate (doc_type dari input Laravel)
- ✅ Progress logging ke Laravel di setiap step
- ✅ Final callback ke Laravel dengan result JSON
- ✅ Support 1 doc_type (essay) dengan fallback

**Panduan Integrasi Backend & Frontend (Test MVP API):**

Untuk koordinasi tim, berikut alur komunikasi data antara Laravel dan AI Agent.

**1. Request dari Laravel ke AI Agent (Trigger):**
Disaat *Frontend* / *Backend* meng-upload PDF, *Backend* (Laravel) menembak URL agent via *Background Process/Queue*:
```bash
curl -X POST http://localhost:8001/api-agent/evaluate \
  -H "X-Internal-Key: super-secret-internal-key-ganti-ini" \
  -H "Content-Type: application/json" \
  -d '{
    "analysis_id": "99", 
    "file_url": "http://localhost:8000/dokumen-user.pdf", 
    "doc_type": "essay"
  }'
```

**2. Immediate Response dari AI Agent:**
Sistem FastAPI langsung mengembalikan token konfirmasi agar *Request* Laravel tidak gantung *(timeout)*:
```json
{
  "task_id": "abcd-1234-xyz",
  "status": "queued"
}
```

**3. Final Callback (Asinkronus ke Laravel):**
Setelah 10-30 detik (bergantung beban OpenAI/Groq), agen AI memanggil URL *callback* milik Laravel *(POST /api/v1/internal/analysis/callback)* dengan membawa *payload* penuh:
```json
{
  "analysis_id": "99",
  "status": "done",
  "result": {
    "analysis_id": "99",
    "doc_type": "essay",
    "title": "Judul Dokumen",
    "page_count": 8,
    "score_overall": 7.95,
    "summary": "Kesimpulan dari evaluasi dokumen...",
    "dimensions": [
      {
        "key": "tesis_argumen",
        "name": "Tesis & Argumen",
        "score": 8.0,
        "weight": 0.25,
        "feedback": "Kritik dan saran terkait tesis..."
      }
      // ... dimensi lainnya ...
    ],
    "overall_feedback": "Saran perbaikan secara general...",
    "strengths": [],
    "improvements": [],
    "references": []
  }
}
```
---

## 8. Fase 3 — Tools & Multi-Agent

> **Goal**: Tambahkan research & bizplan agents, external tools, dan rubrics.
> **Estimasi**: 5-7 hari

### Step 3.1 — External Tools

| Tool | File | Fungsi |
|------|------|--------|
| Web Search | `app/tools/web_search.py` | Tavily API untuk general search |
| Citation Lookup | `app/tools/citation_lookup.py` | arXiv API untuk cari paper relevan |
| Rubric Retriever | `app/tools/rubric_retriever.py` | Load & return rubric markdown |
| Market Search | `app/tools/market_search.py` | Tavily API fokus market data |

### Step 3.2 — Research & Bizplan Agents

- `app/graph/nodes/research_agent.py` — Persona: peer reviewer ICLR-standard
- `app/graph/nodes/bizplan_agent.py` — Persona: VC analyst

### Step 3.3 — Research & Bizplan Prompts

- `app/prompts/research.py` — System prompt reviewer jurnal ilmiah
- `app/prompts/bizplan.py` — System prompt VC/investor analyst

### Step 3.4 — Tool Dispatcher Node

**`app/graph/nodes/tool_dispatcher.py`** — Orchestrate tool calls per doc_type:

```python
# Routing logic:
# Essay    → web_search + rubric_retriever
# Research → citation_lookup + web_search  
# Bizplan  → market_search + web_search
```

### Step 3.5 — Rubric Files

- `data/rubrics/essay_rubric.md`
- `data/rubrics/research_rubric.md`
- `data/rubrics/bizplan_rubric.md`

### Step 3.6 — Update Graph Builder

- Tambahkan `research_agent` dan `bizplan_agent` nodes
- Tambahkan `tool_dispatcher` node di antara agent dan score
- Update conditional edges

### Step 3.7 — Laravel Local Storage Integration

**`app/services/pdf_extractor.py`** — Download PDF dari endpoint internal Laravel sebelum extract:

```python
# httpx (X-Internal-Key) → GET file_url endpoint Laravel → temp file → pymupdf4llm
```

### Step 3.8 — Embedding & Semantic Ranking

Implementasi context optimization:

```
search results (20) → dedup (10-15) → embedding rank (5-8) → final context to LLM (3-5)
```

### Step 3.9 — Unit Tests

- `tests/test_extract.py` — Test PDF extraction
- `tests/test_graph.py` — Test full pipeline (mock LLM)

### ✅ Checkpoint Fase 3

- ✅ 3 doc_types supported (essay, research, bizplan)
- ✅ External tools (web search, citations, rubrics)
- ✅ Integrasi download file dari Laravel local storage
- ✅ Semantic ranking untuk search results
- ✅ Unit tests passing

---

## 9. Fase 4 — Production Ready

> **Goal**: Hardening, error handling, observability, dan deployment.
> **Estimasi**: 3-5 hari

### Step 4.1 — Robust Error Handling

```python
# Setiap node harus:
# 1. Catch exceptions
# 2. Log error ke Laravel
# 3. Set state["error"] dan state["is_valid"] = False
# 4. Graceful degradation (misalnya tools gagal → lanjut tanpa tools)
```

### Step 4.2 — Timeout & Retry

```python
# Per-node timeout
# httpx retry with exponential backoff
# LLM call retry (rate limits)
```

### Step 4.3 — Input Validation & Sanitization

```python
# Validasi di node extract:
# - PDF corrupt → error message yang jelas
# - Terlalu pendek (< 2 halaman) → tolak
# - Terlalu panjang → truncate dengan strategi (intro + conclusion priority)
# - Bukan PDF → reject
```

### Step 4.4 — Observability

```python
# LangSmith tracing (sudah ada config LANGCHAIN_TRACING_V2)
# Python logging (structured JSON logs)
# Request ID tracking end-to-end
```

### Step 4.5 — Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8001
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
```

### Step 4.6 — Rate Limiting & Resource Protection

```python
# FastAPI middleware:
# - Max concurrent pipeline runs
# - Request size limit
# - Timeout per request
```

### Step 4.7 — Security Hardening

```python
# - CORS configuration (hanya allow Laravel origin)
# - Input sanitization
# - No sensitive data in logs
# - Secret rotation support
```

### Step 4.8 — Load Testing

```bash
# Test dengan multiple concurrent requests
# Identifikasi bottleneck (biasanya LLM API calls)
# Tune max workers, timeouts
```

### ✅ Checkpoint Fase 4 (Production Ready)

- ✅ Comprehensive error handling di semua node
- ✅ Timeout & retry strategy
- ✅ Input validation & edge case handling
- ✅ Structured logging & LangSmith tracing
- ✅ Docker containerized
- ✅ Security hardened
- ✅ Load tested

---

## 10. Dependency Map

Urutan implementasi berdasarkan dependency antar file:

```
Fase 1 (Foundation):
  core/config.py      ← PERTAMA (semua file lain depend ke ini)
  core/security.py     ← depend: config.py
  api/schemas.py       ← independen
  services/laravel_client.py ← depend: config.py
  api/routes.py        ← depend: schemas.py, security.py
  main.py              ← depend: api/routes.py

Fase 2 (MVP Pipeline):
  graph/state.py       ← independen (TypedDict)
  graph/nodes/extract.py  ← depend: laravel_client.py
  prompts/essay.py     ← independen (constants)
  graph/nodes/essay_agent.py ← depend: laravel_client.py
  graph/nodes/score.py     ← depend: config.py, laravel_client.py, prompts/
  graph/nodes/generate.py  ← depend: laravel_client.py
  graph/builder.py     ← depend: state.py, semua nodes
  api/routes.py        ← UPDATE: tambah pipeline integration

Fase 3 (Multi-Agent + Tools):
  tools/web_search.py       ← depend: config.py
  tools/citation_lookup.py  ← independen
  tools/rubric_retriever.py ← independen
  tools/market_search.py    ← depend: config.py
  prompts/research.py       ← independen
  prompts/bizplan.py         ← independen
  graph/nodes/research_agent.py ← depend: laravel_client.py
  graph/nodes/bizplan_agent.py  ← depend: laravel_client.py
  graph/nodes/tool_dispatcher.py ← depend: semua tools
  services/pdf_extractor.py  ← depend: config.py (Laravel URL + INTERNAL_KEY)
  graph/builder.py           ← UPDATE: tambah nodes baru
```

---

## 11. Environment Variables

| Variable | Required | Default | Keterangan |
|----------|----------|---------|------------|
| `LARAVEL_URL` | ✅ | `http://localhost:8000` | URL Laravel backend |
| `INTERNAL_KEY` | ✅ | — | Shared secret dengan Laravel |
| `OPENAI_API_KEY` | ✅ | — | OpenAI API key untuk LLM calls |
| `TAVILY_API_KEY` | ⬜ Fase 3 | — | Tavily API key untuk web search |
| `LANGCHAIN_TRACING_V2` | ⬜ Opsional | `false` | Enable LangSmith tracing |
| `LANGCHAIN_API_KEY` | ⬜ Opsional | — | LangSmith API key |

---

## 🗺️ Roadmap Summary

```
┌──────────────────────────────────────────────────────────────┐
│  FASE 1: Foundation (1-2 hari)                               │
│  ☐ Setup folder structure & dependencies                     │
│  ☐ Config + env loader                                       │
│  ☐ Security middleware                                       │ 
│  ☐ API schemas + routes (dummy)                              │
│  ☐ Laravel client service                                    │
│  ☐ Main entrypoint + health check                            │
│  → Deliverable: FastAPI running, /evaluate returns dummy     │
├──────────────────────────────────────────────────────────────┤
│  FASE 2: Core Pipeline / MVP (3-5 hari)                      │
│  ☐ ReviewEngineState TypedDict                               │
│  ☐ Node: extract (PDF → Markdown)                            │
│  ☐ doc_type routing dari input Laravel                       │
│  ☐ Node: essay_agent (context prep)                          │
│  ☐ Prompt: essay system prompt                               │
│  ☐ Node: score (LLM evaluate + weighted scoring)             │
│  ☐ Node: generate (assemble result JSON)                     │
│  ☐ Graph builder (compile pipeline)                          │
│  ☐ Integrate pipeline ke route                               │
│  → Deliverable: End-to-end review untuk essay PDF            │
├──────────────────────────────────────────────────────────────┤
│  FASE 3: Tools & Multi-Agent (5-7 hari)                      │
│  ☐ External tools (web search, citations, rubrics)           │
│  ☐ Research agent + prompt                                   │
│  ☐ Bizplan agent + prompt                                    │
│  ☐ Tool dispatcher node                                      │
│  ☐ Rubric markdown files                                     │
│  ☐ Laravel local storage integration                         │
│  ☐ Embedding & semantic ranking                              │
│  ☐ Unit tests                                                │
│  → Deliverable: Full 3-type support + external tools         │
├──────────────────────────────────────────────────────────────┤
│  FASE 4: Production Ready (3-5 hari)                         │
│  ☐ Error handling + graceful degradation                     │
│  ☐ Timeout & retry strategy                                  │
│  ☐ Input validation & sanitization                           │ 
│  ☐ Structured logging + LangSmith                            │
│  ☐ Dockerfile                                                │
│  ☐ Rate limiting & resource protection                       │
│  ☐ Security hardening                                        │
│  ☐ Load testing                                              │
│  → Deliverable: Production-ready AI agent service            │
└──────────────────────────────────────────────────────────────┘
```

---

> **TIP**: Mulai dari Fase 1 secara berurutan. Jangan skip ke Fase 2 sebelum 
> health check dan dummy endpoint berjalan sempurna. Setiap fase punya 
> checkpoint yang bisa di-test secara independen.
