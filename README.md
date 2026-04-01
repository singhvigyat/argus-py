# 👁️ ARGUS
### *Automated Reasoning for GUI & UX Synthesis*

> Multiple AI agents. One website. Every type of user.

ARGUS is a multi-agent UX testing platform that simulates how different types of users experience your website. Submit a URL — ARGUS deploys a squad of AI persona agents that each independently analyze your UI through their own lens, then synthesizes their findings into a structured, conflict-aware UX report.

**Stack:** Python · FastAPI · asyncio · Pydantic · Playwright · MongoDB

---

## Quick Start

### Prerequisites

- Python 3.11+
- MongoDB (local or Atlas)
- [Gemini API key](https://aistudio.google.com/apikey)

### Setup

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
# Edit .env — set GEMINI_API_KEY and MONGODB_URI
```

### Run

```bash
uvicorn app.main:app --reload --port 8000
```

### Analyze a URL

```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"url": "https://stripe.com", "viewport": "desktop"}'
```

Poll for results:

```bash
curl http://localhost:8000/api/reports/{reportId}
```

List all reports:

```bash
curl http://localhost:8000/api/reports
```

---

## How It Works

```
User submits URL
       │
       ▼
Playwright captures screenshots + DOM extraction + SoM labeling
       │
       ▼
6-stage async pipeline (FastAPI + asyncio)
  1. DOM extraction (bounding boxes + computed styles + sections)
  2. Set-of-Mark screenshot generation
  3. Parallel persona agents (asyncio.gather × 4)
  4. DOM-backed claim verification
  5. Conflict detection (deterministic + semantic)
  6. Report assembly + MongoDB persistence
       │
       ▼
4 persona agents run in parallel
  ├── 👴 Maya — 62-year-old non-technical user
  ├── 👨‍💻 Dev — 24-year-old developer
  ├── 🧭 Arjun — first-time visitor
  └── ♿ Priya — visually impaired user
       │
       ▼
Verified, structured UX report with conflict highlights
```

---

## API Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| `POST` | `/api/analyze` | Start async analysis (`{ url, viewport?, personaIds? }`) |
| `GET` | `/api/reports/:id` | Get report by ID |
| `GET` | `/api/reports` | List all reports |
| `GET` | `/health` | Health check |
| `GET` | `/screenshots/*` | Static screenshot artifacts |

---

## Project Structure

```
app/
├── main.py              # FastAPI application
├── config.py            # Pydantic settings
├── logging_config.py    # Structured logging with trace IDs
├── crawler/             # Playwright capture, DOM extraction, SoM
├── ai/                  # Gemini vision + text with tenacity retries
├── agents/              # Persona definitions + analyzer
├── aggregator/          # Conflict detection, verifier, report builder
├── pipeline/            # 6-stage async orchestrator
├── db/                  # MongoDB persistence (motor)
└── routes/              # REST API
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GEMINI_API_KEY` | Yes | — | Google Gemini API key |
| `MONGODB_URI` | No | `mongodb://localhost:27017` | MongoDB connection string |
| `MONGODB_DATABASE` | No | `argus` | Database name |
| `PORT` | No | `8000` | Server port |
| `PIPELINE_TIMEOUT_SECONDS` | No | `600` | Max pipeline duration |
| `GEMINI_MODEL` | No | `gemini-2.5-flash` | Gemini model |
| `MIN_GEMINI_CALL_DELAY_SECONDS` | No | `20` | Rate-limit spacing between calls |

---

## Technical Highlights

- **Async FastAPI orchestration** — coordinates 4 parallel AI agents via `asyncio.gather` across a 6-stage pipeline
- **Resilient Gemini integration** — tenacity-based retry logic distinguishing rate-limit (429), auth (401), and server (5xx) failures
- **Typed interfaces** — Pydantic models for all agent request/response schemas
- **Production observability** — structured logging with per-job trace IDs and configurable timeout handling
