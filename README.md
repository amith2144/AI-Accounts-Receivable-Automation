# AI Accounts Receivable Automation Platform

An operational finance operations platform for small and medium-sized businesses (SMBs) to automate their invoice-to-cash workflow. The platform ingests invoice documents, maintains real-time receivables aging (Current, 1–30, 31–60, 61–90, 90+ days), tracks payment settlements, and executes automated payment follow-up cadences—serving as an operational automation layer that interfaces with existing accounting software.

---

## Architectural Highlights

- **Backend API & Package Manager:** FastAPI (Python 3.11+) managed with `uv` (Astral) for deterministic lockfiles (`uv.lock`) and fast builds.
- **Persistence & Connection Pooling:** PostgreSQL 16 with SQLAlchemy 2.0 (Async Mapped Declarative) and Alembic migration management with production connection pooling.
- **Edge Gateway & Reverse Proxy:** Nginx (Alpine) for edge rate limiting (10 r/s), SSL/TLS termination, HTTP security headers, and multi-stage static asset serving.
- **Object Storage:** MinIO / S3-compatible API provider abstraction (`providers/storage/`) supporting identical local and cloud storage operations.
- **Distributed Worker & Queue:** Celery + Redis 7 for asynchronous document parsing, nightly aging recalculations, and email reminder dispatch.
- **Document Ingestion Engine:** Multi-tier extraction (PyMuPDF digital extraction + Tesseract OCR fallback) isolated behind `providers/extraction/`.
- **Frontend Client:** React 18 + Vite 5 + TypeScript + Tailwind CSS v3 + `shadcn/ui` + `TanStack Query v5` single-page application with zero Node runtime in production.
- **Layered Architecture:** Strict clean separation between `api/`, `services/`, `repositories/`, `models/`, `database/`, and `providers/`.

---

## Quickstart & Verification

### Running Tests Locally with `uv`
```bash
cd backend
uv sync --extra dev
uv run pytest -v
```

### Starting Container Ecosystem
```bash
docker compose up -d
```
All internal services (Postgres, Redis, MinIO, Backend) run on an isolated bridge network with only gateway ports 80/443 exposed.

