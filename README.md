# 🔬 AI Agent Review Fastrack

> Platform fullstack berbasis AI untuk mengevaluasi dokumen secara otomatis — terinspirasi dari [PaperReview.ai](https://paperreview.ai) (Stanford ML Group).

---

## 📌 Tentang Project

AI Review Engine adalah platform yang menggunakan **AI Agent pipeline** untuk melakukan review dan evaluasi dokumen secara mendalam. Platform ini mendukung tiga jenis dokumen:

| Jenis Dokumen | Persona AI Reviewer | Dimensi Evaluasi |
|---|---|---|
| 📝 **Essay** | Kritikus sastra akademis | Tesis & argumen, struktur, bukti, gaya, orisinalitas |
| 📄 **Karya Ilmiah (Research)** | Peer reviewer standar ICLR | Novelty, signifikansi, metodologi, kejelasan, prior work |
| 💼 **Business Plan** | VC analyst | Problem-solution fit, market size, business model, competitive, financial |

Setiap dokumen yang di-upload akan diproses melalui pipeline AI multi-step dan menghasilkan:
- **Skor keseluruhan** (weighted average)
- **Skor per dimensi** dengan feedback naratif
- **Kekuatan & area perbaikan**
- **Referensi relevan** yang ditemukan dari web/arXiv

---

## 🏗️ Architecture

```
[React Frontend]
       │
       │ REST API + WebSocket
       ▼
[Laravel Backend]  ◄──── callback ────┐
       │                               │
       │ Dispatch Queue Job            │
       ▼                               │
[Laravel Queue Worker]                 │
       │                               │
       │ HTTP POST /evaluate           │
       ▼                               │
[FastAPI AI Agent]  ───────────────────┘
       │
       │ LangGraph Pipeline
       ▼
[AI Review Result]
```

### Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React + Vite + TypeScript + Tailwind CSS + shadcn/ui |
| **Backend** | Laravel 11 + MySQL + Redis + Laravel Reverb (WebSocket) |
| **AI Agent** | FastAPI + LangGraph + LangChain + pymupdf4llm |
| **Queue** | Laravel Queue + Redis |
| **Storage** | S3 / MinIO |
| **Realtime** | Laravel Reverb (WebSocket broadcast) |

---

## 📁 Project Structure

```
ai-review-engine/
├── frontend/          # React + Vite + TypeScript
├── backend/           # Laravel 11 API
├── ai-agent/          # FastAPI + LangGraph AI pipeline
└── technical-implementation.md   # Blueprint arsitektur lengkap
```

---

## ⚡ AI Pipeline (LangGraph)

Dokumen yang di-upload melewati pipeline multi-step:

```
Upload PDF
  → Extract (PDF → Markdown via pymupdf4llm)
  → Validate (panjang, halaman, bahasa)
  → Classify (deteksi jenis dokumen)
  → Agent (persona sesuai doc_type)
  → Tool Dispatch (web search, citation lookup, rubric)
  → Score (weighted evaluation per dimensi)
  → Generate (assemble final review JSON)
  → Callback ke Laravel → WebSocket ke Frontend
```

Progress setiap step di-track **realtime** via WebSocket sehingga user bisa melihat status proses secara live.

---

## 🚀 Getting Started

### Prerequisites

- **Node.js** >= 18
- **PHP** >= 8.2
- **Python** >= 3.11 (managed via [uv](https://docs.astral.sh/uv/))
- **MySQL** 8.x
- **Redis** 7.x
- **Docker** (optional, untuk development dengan containers)

### Development Setup

```bash
# Clone repository
git clone https://github.com/RegiMuhammar/agent-review-fastrack.git
cd agent-review-fastrack

# Frontend
cd frontend
npm install
npm run dev

# Backend
cd backend
composer install
cp .env.example .env
php artisan key:generate
php artisan migrate
php artisan serve

# AI Agent
cd ai-agent
uv sync
uv run main.py

# Queue Worker (terminal terpisah)
cd backend
php artisan queue:work --queue=ai-review,default

# WebSocket Server (terminal terpisah)
cd backend
php artisan reverb:start
```

### Docker (All-in-One)

```bash
docker compose up -d
```

> Menjalankan 8 container: frontend, backend, queue-worker, fastapi, reverb, mysql, redis, minio.

---

## 📋 API Overview

Base URL: `/api/v1`

| Group | Endpoints |
|---|---|
| **Auth** | Register, Login, Logout, Me |
| **User** | Profile, Update, Change Password |
| **Analysis** | Upload PDF, List, Detail, Status, Result, Logs, Delete |
| **Feedback** | Submit rating + comment per analysis |
| **Internal** | AI Agent callback + progress logging (protected) |

> Lihat detail lengkap di [technical-implementation.md](./technical-implementation.md#7-api-design-laravel).

---

## 🔐 Security

- **JWT/Sanctum** — Token-based authentication
- **Internal API Key** — `X-Internal-Key` header untuk endpoint AI callback
- **Upload Validation** — Mime check + max 20MB
- **Ownership Check** — User hanya bisa akses data miliknya
- **CORS** — Hanya allow frontend origin

---

## 📖 Documentation

Dokumentasi arsitektur lengkap tersedia di:
- 📐 [Technical Implementation Blueprint](./technical-implementation.md) — Database design, API design, AI pipeline, queue system, WebSocket, security, dan deployment.

---

## 🤝 Contributing

1. Fork repository ini
2. Buat feature branch (`git checkout -b feature/nama-fitur`)
3. Commit perubahan (`git commit -m 'Add: nama fitur'`)
4. Push ke branch (`git push origin feature/nama-fitur`)
5. Buat Pull Request

---

## 📄 License

This project is private and proprietary.

---

<p align="center">
  Built with ❤️ using AI-powered document analysis
</p>
