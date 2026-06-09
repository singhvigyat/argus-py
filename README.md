# 👁️ ARGUS
### *Automated Reasoning for GUI & UX Synthesis*

> Multiple AI agents. One website. Every type of user.

ARGUS is a multi-agent UX testing platform that simulates how different types of users experience your website. Submit a URL — ARGUS deploys a squad of AI persona agents that each independently analyze your UI through their own lens, then synthesizes their findings into a structured, conflict-aware UX report.

**Stack:** Python · FastAPI · asyncio · Pydantic · Playwright · MongoDB

---

## Why ARGUS?

Traditional UX tools like Hotjar, Maze, and axe-core are:
- **Persona-blind** — they don't reason about *who* is using the interface
- **Rule-based** — they check DOM rules, not visual experience
- **Single-perspective** — one report, no disagreements

ARGUS is different:
- **Visual reasoning** — agents analyze screenshots, not just DOM trees
- **Multi-persona** — each agent has a distinct identity, goals, and pain points
- **Conflict detection** — disagreements between agents surface real UX tensions

---

## How It Works

```
User submits URL
       │
       ▼
Playwright captures screenshots + DOM extraction
       │
       ▼
6-stage async pipeline (FastAPI + asyncio)
       │
       ▼
4 persona agents run in parallel (asyncio.gather)
  ├── 👴 60-year-old non-technical user
  ├── 👨‍💻 22-year-old developer
  ├── ♿ Visually impaired user
  └── 🧭 First-time visitor
       │
       ▼
Vision analysis (Gemini) + conflict detection
       │
       ▼
Verified, structured UX report with conflict highlights
```

---

## Key Features

- **Multi-Agent Architecture** — each persona is a proper agent with its own identity, heuristics, reasoning trace, and structured output schema
- **Visual Reasoning** — agents reason over actual screenshots via the Gemini vision API, complemented by DOM extraction
- **Conflict Detection** — the system flags where personas disagree, surfacing real UX trade-offs
- **Structured Reports** — every agent produces a validated `PersonaAnalysis` Pydantic model; the orchestrator builds the final report from these
- **Parallel Execution** — all persona agents run concurrently via `asyncio.gather` for fast turnaround
- **Full Observability** — structured logging with per-job trace IDs and configurable timeout handling across every pipeline stage

---

## Technical Highlights

AI-native UX testing pipeline that orchestrates multi-agent web interface evaluation via async Python.

- **Async FastAPI orchestration** — built an async FastAPI service that coordinates 4 parallel AI agents via `asyncio.gather` across a 6-stage pipeline: DOM extraction, vision analysis, conflict detection, and verified reporting
- **Resilient Gemini integration** — integrated the Gemini vision API with tenacity-based retry logic, distinguishing rate-limit (429) from auth (401) and server (5xx) failures with per-error fallback routing
- **Typed interfaces throughout** — enforced Pydantic models for all agent request/response schemas, enabling clean provider abstraction and extensibility across AI backends
- **Production observability** — added structured logging with per-job trace IDs and configurable timeout handling, making the async pipeline fully observable across all stages in production

---

## Example Insight

> *"Expert users find the navigation intuitive, but first-time elderly users struggle to locate the primary call-to-action button."*

This kind of cross-persona conflict is invisible to traditional tools. ARGUS surfaces it automatically.
