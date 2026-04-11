# AI Review Engine — Technical Implementation Blueprint

> Versi final yang menggabungkan arsitektur secara mendalam.
> Stack: React + Laravel + FastAPI + LangGraph + Laravel Queue (Redis).

---

## 1. System Overview

Platform fullstack berbasis AI untuk mengevaluasi tiga jenis dokumen: **essay**, **karya ilmiah (research)**, dan **business plan**. Terinspirasi dari paperreview.ai (Stanford ML Group) namun dengan scope lebih luas dan arsitektur yang disesuaikan untuk tim kecil yang scalable secara bertahap.

### Core Stack

| Layer | Teknologi |
|---|---|
| Frontend | React + Vite + TypeScript + Tailwind CSS + shadcn/ui |
| Backend | Laravel 11 + MySQL + Redis + Laravel Reverb (WebSocket) |
| AI Agent | FastAPI + LangGraph + LangChain + pymupdf4llm |
| Queue | Laravel Queue + Redis (queue driver) |
| Storage | S3 / MinIO (file PDF) |
| Realtime | Laravel Reverb (WebSocket broadcast) |

### Keputusan Arsitektur Utama

Queue diletakkan di **backEnd (Laravel Queue)**, bukan di ai-agent. Alasan:

1. Sudah ada Redis untuk Laravel — tidak perlu Redis kedua
2. Hanya Laravel yang menulis ke database (single source of truth)
3. Log terpusat di satu service — lebih mudah debug
4. FastAPI tetap stateless dan pure Python — tidak ada coupling
5. Bisa migrate ke Celery/Dramatiq di ai-agent jika traffic membutuhkan, tanpa rewrite LangGraph

---

## 2. High-Level Architecture

```
[React Frontend]
       │
       │ REST API (Axios + JWT)
       ▼
[Laravel Backend]  ◄──────────────────────────────┐
       │                                           │
       │ 1. Simpan file ke S3/MinIO                │
       │ 2. INSERT analysis (status=pending)       │
       │ 3. TriggerAIReviewJob::dispatch()         │ 6. Callback POST /internal/analysis/callback
       │    → masuk Redis queue                    │    (dari ai-agent setelah LangGraph selesai)
       ▼                                           │
[Laravel Queue Worker]                             │
       │                                           │
       │ 4. Update status=processing               │
       │ 5. HTTP POST ke FastAPI /evaluate         │
       │    (timeout 10 menit)                     │
       ▼                                           │
[FastAPI ai-agent]  ───────────────────────────────┘
       │
       │ Jalankan LangGraph pipeline (async Python)
       ▼
[LangGraph Pipeline]
  extract → classify → agent (essay/research/bizplan)
  → tools (search/citation/rubric) → score → generate
       │
       │ POST callback ke Laravel dengan result JSON
       ▼
[Laravel]
  - UPDATE analysis (status=done, result_json, score)
  - INSERT analysis_logs (step=done)
  - SendEmailNotifJob::dispatch()
  - broadcast(new AnalysisCompleted()) → Reverb WebSocket
       │
       │ WebSocket event
       ▼
[React Frontend]
  ProcessingPage listener → navigate ke /result/{id}
```

---

## 3. Async Flow Detail (Step by Step)

| Step | Siapa | Apa yang terjadi | Sync/Async |
|---|---|---|---|
| 1 | React | POST /api/v1/analysis (upload PDF) | Sync |
| 2 | Laravel | Validasi, simpan S3, INSERT analysis status=pending | Sync |
| 3 | Laravel | Dispatch TriggerAIReviewJob ke Redis queue, return response ke React | Sync → Async start |
| 4 | React | Redirect ke /processing/{id}, subscribe WebSocket channel | — |
| 5 | Queue Worker | Ambil job, update status=processing, POST ke FastAPI /evaluate | Background |
| 6 | FastAPI | Terima request, jalankan `await graph.ainvoke()` | Background |
| 7 | LangGraph | Eksekusi node per node, tiap step POST log ke Laravel /internal/analysis/log | Background |
| 8 | FastAPI | Graph selesai, POST callback ke Laravel /internal/analysis/callback | Background |
| 9 | Laravel | Simpan result_json, update status=done, broadcast WebSocket event | Background |
| 10 | React | Echo listener terima event, navigate ke /result/{id} | Realtime |
| 11 | React | Fetch GET /analysis/{id}/result, tampilkan hasil | Sync |

---

## 4. Web Pages Structure

| # | Halaman | URL | Deskripsi |
|---|---|---|---|
| 1 | Landing / Company Profile | `/` | Hero, features, how it works, CTA |
| 2 | Register | `/register` | Form registrasi |
| 3 | Login | `/login` | Form login |
| 4 | Account / Profile | `/account` | Edit profil, ganti password, statistik |
| 5 | Upload Page | `/upload` | Dropzone PDF + pilih doc_type |
| 6 | Processing Page | `/processing/:id` | Progress tracker realtime via WebSocket |
| 7 | Result Page | `/result/:id` | Skor, dimensi evaluasi, narasi, referensi |
| 8 | History Page | `/history` | List semua analysis + status + filter |
| 9 | Feedback | Bagian dari Result Page | Form rating + komentar |

---

## 5. Frontend Architecture (React)

### Folder Structure

```
frontEnd/
└── src/
    ├── pages/
    │   ├── Landing.tsx
    │   ├── Login.tsx
    │   ├── Register.tsx
    │   ├── Account.tsx
    │   ├── Upload.tsx
    │   ├── Processing.tsx        ← WebSocket listener + progress tracker
    │   ├── Result.tsx            ← Skor + dimensi + narasi + feedback form
    │   └── History.tsx           ← List + pagination + filter
    ├── components/
    │   ├── upload/
    │   │   ├── Dropzone.tsx
    │   │   └── DocTypeSelector.tsx
    │   ├── review/
    │   │   ├── ScoreCard.tsx
    │   │   ├── DimensionList.tsx
    │   │   ├── NarrativeBlock.tsx
    │   │   ├── RelatedWork.tsx
    │   │   └── FeedbackForm.tsx
    │   ├── processing/
    │   │   └── ProgressTracker.tsx   ← Polling logs + step indicator
    │   └── shared/
    │       ├── Navbar.tsx
    │       └── ProtectedRoute.tsx
    ├── hooks/
    │   ├── useWebSocket.ts       ← Laravel Echo subscribe/unsubscribe
    │   ├── useAnalysisLogs.ts    ← Polling GET /analysis/{id}/logs
    │   └── useAuth.ts
    ├── lib/
    │   ├── api.ts                ← Axios instance + interceptors
    │   └── echo.ts               ← Laravel Echo setup (pusher-js)
    ├── store/
    │   └── authStore.ts          ← Zustand + localStorage persist
    └── types/
        ├── analysis.d.ts
        └── user.d.ts
```

### UX Flow

```
User buka app
  ↓
Landing Page → CTA "Mulai Review"
  ↓
Login / Register
  ↓
Upload Page → Pilih file PDF + doc_type → Submit
  ↓
Processing Page
  ├── Subscribe WebSocket channel private-analysis.{userId}
  ├── Poll GET /analysis/{id}/logs setiap 2 detik
  │     → tampilkan: ✔ Ekstraksi dokumen
  │                  ✔ Klasifikasi dokumen
  │                  ⏳ Mencari referensi...
  └── Terima WebSocket event AnalysisCompleted → navigate ke Result
  ↓
Result Page
  ├── Skor keseluruhan (score_overall)
  ├── Skor per dimensi + feedback narasi
  ├── Overall feedback + strengths + improvements
  ├── Referensi / related work yang ditemukan
  └── Form feedback (rating 1-5 + komentar)
  ↓
History Page (kapan saja)
  └── List semua analysis + filter status/doc_type
```

---

## 6. Database Design (MySQL)

### `users`

| Kolom | Tipe | Constraint | Keterangan |
|---|---|---|---|
| id | BIGINT UNSIGNED | PK, AUTO_INCREMENT, NOT NULL | — |
| name | VARCHAR(100) | NOT NULL | — |
| email | VARCHAR(150) | UNIQUE, NOT NULL | — |
| password | VARCHAR(255) | NOT NULL | Bcrypt hash |
| company_name | VARCHAR(150) | NULL | Opsional untuk profil |
| created_at | TIMESTAMP | NULL, DEFAULT CURRENT_TIMESTAMP | — |
| updated_at | TIMESTAMP | NULL, DEFAULT CURRENT_TIMESTAMP ON UPDATE | — |

### `analysis`

| Kolom | Tipe | Constraint | Keterangan |
|---|---|---|---|
| id | BIGINT UNSIGNED | PK, AUTO_INCREMENT, NOT NULL | — |
| user_id | BIGINT UNSIGNED | FK → users.id, NOT NULL | CASCADE DELETE |
| doc_name | VARCHAR(255) | NOT NULL | Nama file original |
| doc_type | ENUM('essay','research','bizplan') | NOT NULL | Ditentukan user saat upload |
| file_path | TEXT | NOT NULL | Path di S3/MinIO |
| status | ENUM('pending','processing','done','failed') | NOT NULL, DEFAULT 'pending' | — |
| task_id | VARCHAR(100) | UNIQUE, NULL | ID dari Laravel job (untuk idempotency) |
| result_json | JSON | NULL | Hasil lengkap dari AI pipeline |
| score_overall | DECIMAL(4,2) | NULL | Skor akhir (derived dari result_json) |
| error_message | TEXT | NULL | Pesan error jika status=failed |
| completed_at | TIMESTAMP | NULL | Waktu selesai diproses |
| created_at | TIMESTAMP | NULL, DEFAULT CURRENT_TIMESTAMP | — |
| updated_at | TIMESTAMP | NULL, DEFAULT CURRENT_TIMESTAMP ON UPDATE | — |

> Tambahan vs versi ChatGPT: `score_overall` (untuk sorting di history tanpa parse JSON), `error_message` (untuk debugging dan tampilan UI failed), `completed_at` (untuk menampilkan durasi proses).

### `analysis_logs`

| Kolom | Tipe | Constraint | Keterangan |
|---|---|---|---|
| id | BIGINT UNSIGNED | PK, AUTO_INCREMENT, NOT NULL | — |
| analysis_id | BIGINT UNSIGNED | FK → analysis.id, NOT NULL | CASCADE DELETE |
| step | VARCHAR(50) | NOT NULL | Nama step pipeline |
| status | ENUM('pending','processing','done','failed') | NOT NULL | Status step ini |
| message | TEXT | NULL | Pesan yang tampil di UI |
| metadata_json | JSON | NULL | Data teknis (opsional, untuk debug) |
| created_at | TIMESTAMP | NULL, DEFAULT CURRENT_TIMESTAMP | — |

> Nilai `step` yang valid: `extracting`, `classifying`, `preparing`, `searching`, `ranking`, `scoring`, `generating`, `done`

### `feedbacks`

| Kolom | Tipe | Constraint | Keterangan |
|---|---|---|---|
| id | BIGINT UNSIGNED | PK, AUTO_INCREMENT, NOT NULL | — |
| analysis_id | BIGINT UNSIGNED | FK → analysis.id, NOT NULL | CASCADE DELETE |
| user_id | BIGINT UNSIGNED | FK → users.id, NOT NULL | Untuk memastikan owner yang submit |
| rating | TINYINT UNSIGNED | NOT NULL | Range 1–5 |
| comment | TEXT | NULL | — |
| created_at | TIMESTAMP | NULL, DEFAULT CURRENT_TIMESTAMP | — |

> Tambahan vs versi ChatGPT: `user_id` (untuk validasi hanya owner yang bisa submit feedback dan idempotency check).

---

## 7. API Design (Laravel)

### Base URL

```
/api/v1
```

### Standard Response Format

```json
{
  "success": true,
  "data": { ... },
  "message": "OK"
}
```

Error response:

```json
{
  "success": false,
  "message": "Pesan error yang user-friendly",
  "errors": { "field": ["detail error"] }
}
```

---

### Auth

| Method | Endpoint | Auth | Body / Notes |
|---|---|---|---|
| POST | `/auth/register` | — | name, email, password |
| POST | `/auth/login` | — | email, password → return token + user |
| POST | `/auth/logout` | Bearer | Revoke current token |
| GET | `/auth/me` | Bearer | Return authenticated user |

---

### User / Account

| Method | Endpoint | Auth | Notes |
|---|---|---|---|
| GET | `/user/profile` | Bearer | Return user + statistik ringkas |
| PUT | `/user/profile` | Bearer | Update name, company_name |
| PUT | `/user/password` | Bearer | current_password + new_password |

---

### Analysis (Core Feature)

| Method | Endpoint | Auth | Notes |
|---|---|---|---|
| POST | `/analysis` | Bearer | Form-data: file (PDF, max 20MB), doc_type |
| GET | `/analysis` | Bearer | List semua milik user. Query: ?page, ?status, ?doc_type |
| GET | `/analysis/{id}` | Bearer | Detail lengkap (jika done: sertakan result) |
| DELETE | `/analysis/{id}` | Bearer | Soft delete atau hard delete |
| GET | `/analysis/{id}/status` | Bearer | Lightweight: hanya return id + status + score_overall |
| GET | `/analysis/{id}/result` | Bearer | Full result_json dalam format yang sudah di-parse |
| GET | `/analysis/{id}/logs` | Bearer | List analysis_logs — untuk progress tracker UI |
| POST | `/analysis/{id}/feedback` | Bearer | rating (1-5) + comment |
| GET | `/analysis/{id}/feedback` | Bearer | Return feedback milik analysis ini |

---

### Internal (AI Callback — tidak expose ke publik)

| Method | Endpoint | Auth | Notes |
|---|---|---|---|
| POST | `/internal/analysis/callback` | API Key header | Dipanggil oleh ai-agent setelah pipeline selesai |
| POST | `/internal/analysis/log` | API Key header | Dipanggil ai-agent per step untuk update progress |

> Keduanya dilindungi header `X-Internal-Key: {secret}` yang hanya diketahui ai-agent service. Bukan public endpoint.

---

### Laravel Routing (api.php)

```php
Route::prefix('v1')->group(function () {

    // AUTH
    Route::prefix('auth')->group(function () {
        Route::post('/register', [AuthController::class, 'register']);
        Route::post('/login',    [AuthController::class, 'login']);
        Route::middleware('auth:sanctum')->group(function () {
            Route::post('/logout', [AuthController::class, 'logout']);
            Route::get('/me',      [AuthController::class, 'me']);
        });
    });

    // PUBLIC
    Route::get('/company', [CompanyController::class, 'index']);

    // PROTECTED
    Route::middleware('auth:sanctum')->group(function () {

        // USER
        Route::prefix('user')->group(function () {
            Route::get('/profile',  [UserController::class, 'show']);
            Route::put('/profile',  [UserController::class, 'update']);
            Route::put('/password', [UserController::class, 'changePassword']);
        });

        // ANALYSIS
        Route::prefix('analysis')->group(function () {
            Route::post('/',               [AnalysisController::class, 'store']);
            Route::get('/',                [AnalysisController::class, 'index']);
            Route::get('/{id}',            [AnalysisController::class, 'show']);
            Route::delete('/{id}',         [AnalysisController::class, 'destroy']);
            Route::get('/{id}/status',     [AnalysisController::class, 'status']);
            Route::get('/{id}/result',     [AnalysisController::class, 'result']);
            Route::get('/{id}/logs',       [AnalysisController::class, 'logs']);
            Route::post('/{id}/feedback',  [FeedbackController::class, 'store']);
            Route::get('/{id}/feedback',   [FeedbackController::class, 'show']);
        });
    });

    // INTERNAL — hanya dari ai-agent service, dilindungi middleware
    Route::middleware('internal.key')->prefix('internal')->group(function () {
        Route::post('/analysis/callback', [InternalController::class, 'callback']);
        Route::post('/analysis/log',      [InternalController::class, 'log']);
    });

});
```

### Page ↔ API Mapping

| Halaman | API yang dipakai |
|---|---|
| Landing | `GET /company` |
| Login | `POST /auth/login` |
| Register | `POST /auth/register` |
| Account | `GET /user/profile`, `PUT /user/profile`, `PUT /user/password` |
| Upload | `POST /analysis` |
| Processing | `GET /analysis/{id}/logs` (polling 2s), WebSocket event |
| Result | `GET /analysis/{id}/result`, `POST /analysis/{id}/feedback` |
| History | `GET /analysis?page=&status=&doc_type=` |

---

## 8. Backend Jobs (Laravel Queue)

Semua job berjalan di background via `php artisan queue:work --queue=ai-review,default`.

| Job | Queue | Triggered by | Yang dilakukan |
|---|---|---|---|
| `TriggerAIReviewJob` | `ai-review` | `AnalysisController@store` | Update status=processing, POST ke FastAPI, handle error |
| `SaveAnalysisResultJob` | `default` | `InternalController@callback` | Update DB result, dispatch email + broadcast |
| `SendEmailNotifJob` | `default` | `SaveAnalysisResultJob` | Kirim email notifikasi selesai / gagal |

### TriggerAIReviewJob

```php
class TriggerAIReviewJob implements ShouldQueue
{
    public $tries   = 3;
    public $timeout = 660;           // 11 menit
    public $backoff = [60, 120, 240]; // exponential retry

    public function handle(AIAgentService $ai): void
    {
        $this->analysis->update(['status' => 'processing']);

        try {
            // POST ke FastAPI — blocking di job ini, non-blocking untuk user
            $response = $ai->evaluate($this->analysis);
            // FastAPI return {"task_id": "...", "status": "queued"}
            $this->analysis->update(['task_id' => $response['task_id']]);
        } catch (Exception $e) {
            $this->analysis->update([
                'status'        => 'failed',
                'error_message' => $e->getMessage(),
            ]);
            broadcast(new AnalysisFailed($this->analysis));
        }
    }

    public function failed(Throwable $e): void
    {
        // Dipanggil setelah semua retry habis
        $this->analysis->update(['status' => 'failed', 'error_message' => $e->getMessage()]);
        broadcast(new AnalysisFailed($this->analysis));
        SendEmailNotifJob::dispatch($this->analysis, 'failed');
    }
}
```

---

## 9. AI Agent Architecture (FastAPI + LangGraph)

### Folder Structure

```
aiAgent/
├── app/
│   ├── api/
│   │   ├── routes.py          ← POST /evaluate
│   │   └── schemas.py         ← Pydantic request/response models
│   ├── graph/
│   │   ├── state.py           ← ReviewEngineState TypedDict
│   │   ├── builder.py         ← Compile graph + conditional edges
│   │   └── nodes/
│   │       ├── extract.py     ← PDF → Markdown (pymupdf4llm)
│   │       ├── classify.py    ← LLM classify doc_type
│   │       ├── essay_agent.py
│   │       ├── research_agent.py
│   │       ├── bizplan_agent.py
│   │       ├── tool_dispatcher.py
│   │       ├── score.py       ← Weighted average scoring
│   │       └── generate.py    ← Assemble final JSON
│   ├── tools/
│   │   ├── web_search.py      ← Tavily API
│   │   ├── citation_lookup.py ← arXiv API
│   │   ├── rubric_retriever.py← Load rubrik dari file
│   │   └── market_search.py   ← Web search fokus market data
│   ├── prompts/
│   │   ├── essay.py           ← Persona: kritikus sastra
│   │   ├── research.py        ← Persona: peer reviewer ICLR-standard
│   │   └── bizplan.py         ← Persona: VC analyst
│   ├── services/
│   │   ├── pdf_extractor.py
│   │   └── laravel_client.py  ← HTTP client untuk callback + log ke Laravel
│   └── core/
│       ├── config.py          ← Settings dari .env
│       └── security.py        ← Validasi X-Internal-Key
├── data/
│   └── rubrics/
│       ├── essay_rubric.md
│       ├── research_rubric.md
│       └── bizplan_rubric.md
├── main.py
└── requirements.txt
```

### LangGraph Pipeline

```
START
  ↓
[extract]       Download PDF dari S3 → Markdown via pymupdf4llm
  ↓
[validate]      Cek panjang, halaman min 2, bahasa
  ↓ (is_valid=False → END dengan error)
[classify]      LLM classify → doc_type + confidence
  ↓ (conditional edge berdasarkan doc_type)
  ├── "essay"    → [essay_agent]
  ├── "research" → [research_agent]
  └── "bizplan"  → [bizplan_agent]
                      ↓
                [tool_dispatcher]   Jalankan tools sesuai doc_type
                  ├── Essay: web_search + rubric_retriever
                  ├── Research: citation_lookup + web_search
                  └── Bizplan: market_search + web_search
                      ↓
                [score]             LLM evaluate + weighted scoring
                      ↓
                [generate]          Assemble final_result JSON
                      ↓
                    END → POST callback ke Laravel
```

### ReviewEngineState (TypedDict)

```python
class ReviewEngineState(TypedDict):
    # Input
    analysis_id:   str
    file_path:     str
    doc_type_hint: str | None

    # Extraction
    raw_markdown:  str
    page_count:    int
    title:         str | None
    is_valid:      bool
    error:         str | None

    # Classification
    doc_type:             Literal["essay", "research", "bizplan"] | None
    classify_confidence:  float

    # Agent prep
    agent_context:   str
    search_queries:  list[str]

    # Tools
    tool_results: Annotated[list[dict], operator.add]  # akumulasi

    # Scoring
    dimension_scores:     dict[str, float]
    score_overall:        float | None
    dimensions_feedback:  list[dict]
    overall_feedback:     str
    summary:              str

    # Final
    final_result: dict | None
```

### Dimension Weights per Doc Type

```python
DIMENSION_WEIGHTS = {
    "essay": {
        "tesis_argumen": 0.25, "struktur":    0.20,
        "bukti":         0.20, "gaya":        0.15,
        "orisinalitas":  0.10, "simpulan":    0.10,
    },
    "research": {
        "novelty":       0.25, "signifikansi": 0.20,
        "metodologi":    0.20, "kejelasan":    0.15,
        "prior_work":    0.10, "kontribusi":   0.10,
    },
    "bizplan": {
        "problem_solution": 0.25, "market_size":   0.20,
        "business_model":   0.20, "competitive":   0.15,
        "team":             0.10, "financial":     0.10,
    },
}
```

### Progress Logging dari ai-agent ke Laravel

Setiap kali node selesai dieksekusi, ai-agent POST ke Laravel:

```python
# services/laravel_client.py
async def log_step(analysis_id: str, step: str, status: str, message: str):
    await httpx.post(
        f"{settings.LARAVEL_URL}/api/v1/internal/analysis/log",
        headers={"X-Internal-Key": settings.INTERNAL_KEY},
        json={
            "analysis_id": analysis_id,
            "step": step,         # "extracting", "classifying", dst
            "status": status,     # "processing" atau "done"
            "message": message,   # Tampil di UI: "Mengekstrak dokumen..."
        }
    )

# Contoh pemanggilan di setiap node:
await log_step(state["analysis_id"], "extracting",  "done",       "Dokumen berhasil diekstrak")
await log_step(state["analysis_id"], "classifying", "done",       "Dokumen dikenali sebagai Essay")
await log_step(state["analysis_id"], "searching",   "processing", "Mencari referensi relevan...")
```

---

## 10. Result JSON Structure

Format `result_json` yang disimpan di kolom `analysis.result_json`:

```json
{
  "analysis_id": "123",
  "doc_type": "essay",
  "score_overall": 7.8,
  "summary": "Essay ini memiliki argumen yang kuat dengan struktur yang baik...",
  "dimensions": [
    {
      "name": "Tesis & Argumen",
      "key": "tesis_argumen",
      "score": 8.5,
      "weight": 0.25,
      "feedback": "Posisi penulis jelas sejak paragraf pembuka. Argumen didukung dengan..."
    },
    {
      "name": "Struktur & Koherensi",
      "key": "struktur",
      "score": 7.0,
      "weight": 0.20,
      "feedback": "Alur antar paragraf cukup logis, namun transisi di bagian ketiga..."
    }
  ],
  "overall_feedback": "Secara keseluruhan, essay ini menunjukkan kemampuan argumentasi yang baik...",
  "strengths": [
    "Argumen utama didukung data empiris yang kuat",
    "Gaya bahasa akademis dan konsisten"
  ],
  "improvements": [
    "Perlu memperkuat konteks latar belakang di paragraf pembuka",
    "Referensi bisa ditambah dari sumber primer"
  ],
  "references": [
    {
      "title": "The Role of Argumentation in Academic Writing",
      "authors": "Smith, J. et al.",
      "url": "https://arxiv.org/...",
      "year": 2023,
      "relevance": "Mendukung klaim di bagian 3"
    }
  ],
  "processing_time_seconds": 87
}
```

---

## 11. Context Optimization Strategy (LangGraph Pipeline)

Mengikuti pendekatan paperreview.ai untuk menjaga kualitas hasil tanpa membanjiri context window LLM.

| Stage | Jumlah | Strategi |
|---|---|---|
| Search queries yang digenerate | 3–5 | Variasi: topik utama, argumen kunci, konteks bidang |
| Raw search results | 20 | Ambil dari Tavily / arXiv |
| Setelah deduplication | 10–15 | Dedup berdasarkan URL + similarity judul |
| Setelah embedding ranking | 5–8 | Cosine similarity terhadap dokumen asli |
| Final context ke LLM | 3–5 | Abstract saja, atau full text jika sangat relevan |

### Aturan Summarization

- **Jangan** summarize semua hasil mentah lebih awal
- Summarize **hanya** top-K yang sudah di-ranking
- Gunakan **structured context** — bukan blob teks panjang

```python
# Format konteks yang dikirim ke LLM scorer
structured_context = """
DOKUMEN YANG DIEVALUASI:
{raw_markdown[:6000]}

REFERENSI RELEVAN YANG DITEMUKAN:
1. [{title}] {abstract[:300]}...
2. [{title}] {abstract[:300]}...

RUBRIK EVALUASI:
{rubric_content}
"""
```

---

## 12. Embedding Usage

Digunakan untuk semantic ranking hasil search sebelum masuk ke LLM — bukan untuk vector store permanen.

```
Embedding(dokumen_asli)         → vektor dokumen
Embedding(search_result_i)      → vektor tiap hasil
→ cosine_similarity(dokumen, result_i) → skor relevansi
→ sort descending → ambil top-K
```

Implementasi: `langchain_openai.OpenAIEmbeddings` dengan model `text-embedding-3-small`.

---

## 13. Realtime: WebSocket (Laravel Reverb)

### Event yang di-broadcast

| Event | Channel | Payload | Trigger |
|---|---|---|---|
| `AnalysisCompleted` | `private-analysis.{userId}` | `{analysis_id, status, score_overall, doc_type}` | Setelah `SaveAnalysisResultJob` |
| `AnalysisFailed` | `private-analysis.{userId}` | `{analysis_id, status, error_message}` | Setelah semua retry habis |

### React Setup (Laravel Echo)

```typescript
// lib/echo.ts
import Echo from 'laravel-echo'
import Pusher from 'pusher-js'

window.Pusher = Pusher
window.Echo = new Echo({
  broadcaster: 'reverb',
  key: import.meta.env.VITE_REVERB_APP_KEY,
  wsHost: import.meta.env.VITE_REVERB_HOST,
  wsPort: import.meta.env.VITE_REVERB_PORT,
  forceTLS: false,
  enabledTransports: ['ws'],
})

// hooks/useWebSocket.ts — digunakan di ProcessingPage
export function useAnalysisChannel(userId: number, analysisId: number) {
  useEffect(() => {
    const channel = window.Echo
      .private(`analysis.${userId}`)
      .listen('.AnalysisCompleted', (e: any) => {
        if (e.analysis_id === analysisId) navigate(`/result/${analysisId}`)
      })
      .listen('.AnalysisFailed', (e: any) => {
        if (e.analysis_id === analysisId) setError(e.error_message)
      })

    // Fallback: jika WS tidak connect dalam 5s, aktifkan polling
    const fallbackTimer = setTimeout(() => {
      if (!isWsConnected) startStatusPolling()
    }, 5000)

    return () => {
      channel.stopListening('.AnalysisCompleted')
      clearTimeout(fallbackTimer)
      stopPolling()
    }
  }, [analysisId])
}
```

---

## 14. Security

### Lapisan Keamanan

| Lapisan | Mekanisme | Keterangan |
|---|---|---|
| Autentikasi user | Laravel Sanctum (token-based) | Semua endpoint protected butuh Bearer token |
| Internal endpoint | `X-Internal-Key` header | Hanya ai-agent yang tahu nilainya, via env var |
| Validasi upload | Mime check + size limit | mimes:pdf, max:20480 KB |
| Ownership check | Policy / where clause | `analysis.user_id = auth()->id()` |
| Idempotency | Cek status sebelum proses | `SaveAnalysisResultJob` skip jika sudah done |
| CORS | Laravel CORS config | Hanya allow frontend origin |

### Middleware `internal.key`

```php
// app/Http/Middleware/ValidateInternalKey.php
public function handle(Request $request, Closure $next): Response
{
    $key = $request->header('X-Internal-Key');
    if ($key !== config('services.internal.key')) {
        return response()->json(['message' => 'Forbidden'], 403);
    }
    return $next($request);
}
```

---

## 15. Docker Compose Services

```yaml
services:
  frontend:
    build: ./frontEnd
    ports: ["5173:5173"]

  backend:
    build: ./backEnd
    ports: ["8000:8000"]
    depends_on: [mysql, redis]
    environment:
      QUEUE_CONNECTION: redis
      REDIS_HOST: redis

  queue-worker:
    build: ./backEnd
    command: php artisan queue:work --queue=ai-review,default --tries=3
    depends_on: [mysql, redis]
    restart: unless-stopped

  fastapi:
    build: ./aiAgent
    ports: ["8001:8001"]
    depends_on: [redis]

  reverb:
    build: ./backEnd
    command: php artisan reverb:start
    ports: ["8080:8080"]

  mysql:
    image: mysql:8
    ports: ["3306:3306"]
    volumes: ["mysql_data:/var/lib/mysql"]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  minio:
    image: minio/minio
    ports: ["9000:9000", "9001:9001"]
    command: server /data --console-address ":9001"
    volumes: ["minio_data:/data"]

volumes:
  mysql_data:
  minio_data:
```

> **8 container total** — tidak ada Redis kedua, tidak ada Dramatiq/Celery worker terpisah.

---

## 16. Logging Strategy

Setiap step pipeline ditulis ke tabel `analysis_logs` via endpoint internal Laravel.

| Step value | Pesan UI | Timing |
|---|---|---|
| `extracting` | "Membaca dan mengekstrak dokumen..." | Node extract mulai |
| `classifying` | "Mengidentifikasi jenis dokumen..." | Node classify mulai |
| `preparing` | "Menyiapkan analisis {doc_type}..." | Node agent mulai |
| `searching` | "Mencari referensi relevan..." | Node tool_dispatcher mulai |
| `scoring` | "Mengevaluasi dan memberi skor..." | Node score mulai |
| `generating` | "Menyusun laporan evaluasi..." | Node generate mulai |
| `done` | "Evaluasi selesai!" | Setelah callback berhasil |

React poll `GET /analysis/{id}/logs` setiap 2 detik di ProcessingPage untuk menampilkan progress tracker step-by-step.

---

## 17. Scaling Plan

Untuk skala awal (MVP hingga ratusan request/hari), arsitektur saat ini sudah cukup. Jika perlu scale:

| Kebutuhan | Solusi |
|---|---|
| Lebih banyak concurrent AI jobs | Tambah instance `queue-worker` container |
| FastAPI overload | Scale horizontal FastAPI dengan load balancer |
| Redis single point of failure | Redis Sentinel atau Redis Cluster |
| File storage besar | Sudah pakai S3/MinIO — tinggal tambah kapasitas |
| Migrasi queue ke ai-agent | Tambah Celery di aiAgent, ubah TriggerAIReviewJob jadi non-blocking (tidak perlu rewrite LangGraph) |

---

## 18. Future Enhancements

| Fitur | Keterangan |
|---|---|
| Vector DB (ChromaDB / pgvector) | Simpan rubrik dan referensi secara permanen, query semantik |
| Multi-agent discussion | Beberapa reviewer persona berdiskusi sebelum final verdict (MARG pattern) |
| Streaming response | FastAPI SSE → React tampilkan review karakter per karakter |
| Re-ranking dengan LLM | Ganti cosine similarity dengan LLM-based relevance scoring |
| Persona kustom | User bisa pilih gaya reviewer (strict academic / constructive mentor / industry expert) |
| Batch review | Upload beberapa dokumen sekaligus |
| Export PDF | Hasil review bisa di-export sebagai PDF report |

---

## 19. Environment Variables

### backEnd/.env

```env
APP_NAME="AI Review Engine"
APP_URL=http://localhost:8000

DB_CONNECTION=mysql
DB_HOST=mysql
DB_DATABASE=ai_review
DB_USERNAME=root
DB_PASSWORD=secret

QUEUE_CONNECTION=redis
REDIS_HOST=redis
REDIS_PORT=6379

FILESYSTEM_DISK=s3
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
AWS_DEFAULT_REGION=us-east-1
AWS_BUCKET=ai-review
AWS_URL=http://minio:9000
AWS_ENDPOINT=http://minio:9000
AWS_USE_PATH_STYLE_ENDPOINT=true

REVERB_APP_ID=ai-review
REVERB_APP_KEY=local-key
REVERB_APP_SECRET=local-secret
REVERB_HOST=reverb
REVERB_PORT=8080

AI_AGENT_URL=http://fastapi:8001
AI_AGENT_TIMEOUT=600

INTERNAL_KEY=super-secret-internal-key-ganti-ini

MAIL_MAILER=smtp
MAIL_HOST=smtp.mailgun.org
MAIL_PORT=587
```

### aiAgent/.env

```env
LARAVEL_URL=http://backend:8000
INTERNAL_KEY=super-secret-internal-key-ganti-ini

OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...

S3_ENDPOINT=http://minio:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET=ai-review

LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls-...
```

### frontEnd/.env

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_REVERB_APP_KEY=local-key
VITE_REVERB_HOST=localhost
VITE_REVERB_PORT=8080
```

---

## FINAL NOTE

Arsitektur ini adalah **production-ready baseline** yang pragmatis untuk membangun AI Review Engine serupa PaperReview.ai (Stanford ML Group) namun dengan scope lebih luas (essay, research, bizplan) dan stack yang maintainable untuk tim kecil.

Prinsip utama yang dipegang:

1. **Satu source of truth** — hanya Laravel yang menulis ke MySQL
2. **Separation of concerns** — AI logic tetap di Python, orchestration di Laravel
3. **Progressive complexity** — mulai sederhana, scale saat benar-benar dibutuhkan
4. **UX-first** — progress tracking realtime + WebSocket untuk pengalaman yang responsif

