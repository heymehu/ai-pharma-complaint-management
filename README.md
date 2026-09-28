# AIVOA Complaint Management System

AI-powered pharmaceutical complaint management for quality teams — log, analyze, investigate, and resolve customer complaints with an AI Copilot that auto-fills forms from emails, documents, and voice.

## Architecture

| Layer | Stack |
|-------|--------|
| Frontend | Next.js 15+, React 19, TypeScript, Tailwind CSS, Framer Motion, Zod, React Hook Form |
| Backend | FastAPI, SQLAlchemy, PostgreSQL (SQLite locally) |
| AI | Google Gemini, document OCR/PDF extraction |
| Auth | JWT (Clerk/Auth.js ready) |
| Deploy | Vercel (frontend), Railway (backend), Docker Compose |

## Quick Start

### 1. Backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
# Optional for PostgreSQL:
# pip install psycopg2-binary

copy .env.example .env   # or edit .env
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

Default users (seeded):
- `admin@aivoa.com` / `admin123`
- `qa@aivoa.com` / `qa123456`

### 2. Frontend

```bash
cd frontend
npm install
# optional: set NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
npm run dev
```

App: http://localhost:3000

### 3. Docker Compose

```bash
docker compose up --build
```

## Demo Workflow

1. Open http://localhost:3000 — split screen: **Complaint Form (65%)** | **AI Copilot (35%)**
2. Copilot greets: *"Ready to process new complaints..."*
3. Paste this example into the chat:

```
Apollo Pharmacy reported discolored capsules in batch DGH-287FDA. Expiry Feb 2029. Customer suspects contamination.
```

4. AI extracts Product, Batch, Customer, Expiry, Summary and fills the form with animated field highlights
5. AI Suggested Investigation cards appear (Potential Issue, Suggested Test, Priority, Recommended Action)
6. Use quick actions: Summarize, Investigate, CAPA, FDA Report, Customer Reply
7. Save complaint, advance lifecycle status, download audit-ready PDFs

## AI Configuration

In `.env` (or `backend/.env`):

```env
AI_PROVIDER=gemini        # gemini | mock
GOOGLE_API_KEY=           # Google AI Studio API key
GEMINI_MODEL=gemini-2.5-flash
```

Gemini powers complaint extraction and the copilot using `gemini-2.5-flash`. `mock` mode uses rule-based extraction offline; if Gemini is unavailable, extraction falls back to the local extractor.

## Features

- Split-screen complaint workspace + AI Copilot
- Auto form fill from email / PDF / Word / images / voice
- AI investigation, CAPA, customer reply, FDA outline
- Complaint lifecycle: Pending → Under Review → Investigation → CAPA → Closed
- Dashboard stats & charts
- Global search

- PDF report generation
- Role-ready auth (Admin, QA Manager, QA Executive, Investigator, Auditor, Viewer)
- Audit logging

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── api/routes.py
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   └── services/ai/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/app/
│   ├── src/components/
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

## Deployment

- **Vercel:** import the repository root. `vercel.json` deploys the Next.js frontend and FastAPI backend as services and routes `/api/*` to the backend.
- **Persistent data:** configure `DATABASE_URL` to a PostgreSQL database for production. SQLite is suitable only for local development or temporary demos.
- **AI:** set `GOOGLE_API_KEY` in Vercel project environment variables to enable Gemini extraction and copilot features.
- **Docker:** `docker compose up --build`
