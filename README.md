# ARGUS

Automated Reasoning for GUI & UX Synthesis.

Python port of [ux-testing-platform](https://github.com/singhvigyat/ux-testing-platform). Same React frontend. FastAPI backend.

Submit a URL. Four persona agents read the interface independently. The report surfaces issues, conflicts, and verified claims.

**Stack:** FastAPI · asyncio · Pydantic · Playwright · Gemini Vision · React + Vite

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- [Gemini API key](https://aistudio.google.com/apikey)
- Google OAuth Web client ID

### 1. Backend

```bash
cd argus-py
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
playwright install chromium

cp .env.example .env
# Edit .env — GEMINI_API_KEY, GOOGLE_CLIENT_ID, SESSION_SECRET
```

Generate a session secret:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Run:

```bash
uvicorn app.main:app --reload --port 8000
```

MongoDB is optional. If `MONGODB_URI` is empty, jobs stay in memory.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Vite proxies `/api` and `/screenshots` to port 8000.

### Google Sign-In

Same flow as the TypeScript app:

1. Google Cloud Console → Credentials → OAuth client ID → Web application
2. Authorized JavaScript origins: `http://localhost:5173`
3. Put the client ID in `GOOGLE_CLIENT_ID`
4. OAuth consent screen: External, scopes `email` `profile` `openid`, **Publish app**

Each Google account gets `DAILY_ANALYSIS_LIMIT` readings per UTC day (default 3). `GLOBAL_DAILY_LIMIT` caps the whole server.

---

## How It Works

```
URL Input → POST /api/analyze
    │
    ▼
6-stage async pipeline (FastAPI + asyncio)
  1. DOM extraction + Playwright screenshots
  2. Set-of-Mark screenshot generation
  3. Parallel persona agents (asyncio.gather × 4)
  4. DOM-backed claim verification
  5. Conflict detection (deterministic + semantic)
  6. Verified report assembly
    │
    ▼
Frontend polls GET /api/analyze/:jobId
    │
    ▼
React displays structured UX report
```

Personas: Maya (elderly), Dev (engineer), Arjun (first visit), Priya (low vision).

---

## API

| Method | Route | Description |
|---|---|---|
| `POST` | `/api/analyze` | Start analysis (`{ url, personaIds? }`). Needs Google session. |
| `GET` | `/api/analyze/:jobId` | Poll job status + report |
| `GET` | `/api/auth/config` | Google client ID + quota limits |
| `GET` | `/api/auth/me` | Current user + quota |
| `POST` | `/api/auth/google` | `{ credential }` Google ID token |
| `POST` | `/api/auth/logout` | Clear session cookie |
| `GET` | `/health` | Health check |
| `GET` | `/screenshots/*` | Screenshot artifacts |

`POST /api/analyze` response:

```json
{ "jobId": "uuid", "message": "Analysis started", "quota": { "used": 1, "limit": 3, "remaining": 2, "resetAt": "..." } }
```

---

## Project Structure

```
argus-py/
├── app/
│   ├── main.py              # FastAPI app, CORS, cookies
│   ├── config.py            # Pydantic settings
│   ├── logging_config.py    # Structured logs with per-job trace IDs
│   ├── crawler/             # Playwright capture, DOM extraction, SoM
│   ├── ai/                  # VisionProvider + Gemini retries/fallback
│   ├── agents/              # Persona definitions + analyzer
│   ├── aggregator/          # Verifier, conflicts, report builder
│   ├── pipeline/            # 6-stage async orchestrator
│   ├── auth/                # Google ID token, JWT cookie, quotas
│   ├── db/                  # In-memory jobs + optional MongoDB
│   └── routes/              # /api/analyze, /api/auth
└── frontend/                # React + Vite + Tailwind (copied as-is)
```

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `GEMINI_API_KEY` | Yes | — | Google Gemini API key |
| `GOOGLE_CLIENT_ID` | Yes | — | Google OAuth Web client ID |
| `SESSION_SECRET` | Yes | — | JWT cookie signing secret |
| `FRONTEND_URL` | Production | `http://localhost:5173` | CORS origin |
| `GEMINI_MODEL` | No | `gemini-2.5-flash` | Primary model |
| `GEMINI_FALLBACK_MODEL` | No | `gemini-2.0-flash` | Used after 5xx retries |
| `GEMINI_TIMEOUT_SECONDS` | No | `120` | Per Gemini call timeout |
| `PIPELINE_TIMEOUT_SECONDS` | No | `600` | Max full pipeline duration |
| `MIN_GEMINI_CALL_DELAY_SECONDS` | No | `20` | Spacing between Gemini calls |
| `DAILY_ANALYSIS_LIMIT` | No | `3` | Per-account UTC daily cap |
| `GLOBAL_DAILY_LIMIT` | No | `40` | Server-wide UTC daily cap |
| `MONGODB_URI` | No | empty | Optional persistence |
| `PORT` | No | `8000` | Backend port |
| `VITE_API_URL` | Production | empty | Frontend: backend URL, no trailing slash |

---

## Technical Highlights

- Async FastAPI orchestration — 4 parallel AI agents via `asyncio.gather` across a 6-stage pipeline
- Gemini vision with tenacity retries — 429 backoff, 401 fail-fast, 5xx retry then fallback model
- Pydantic models for every agent request/response schema and a `VisionProvider` protocol for other backends
- Structured logging with per-job trace IDs and configurable pipeline/call timeouts
