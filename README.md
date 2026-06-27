# OptiMiles

**The most trustworthy AI reward strategist for Indian travel rewards.**

OptiMiles is an AI-powered reward optimization and financial decision intelligence platform focused on Indian credit cards, airline miles, transfer partners, reward simulations, and goal-based travel optimization.

You tell it a goal — *"I want to fly Singapore Airlines business class in 8 months"* — and OptiMiles works out the optimal card strategy, reward accumulation plan, transfer recommendations, and spend routing to get you there, with every recommendation explainable and traceable back to deterministic logic.

> Think of it as **Google Maps for Indian credit card rewards.**

---

## What OptiMiles is (and isn't)

**It is** a reward optimization engine, a financial decision intelligence system, and an explainable travel-reward strategy platform.

**It is not** a generic chatbot, a card comparison website, a broad fintech dashboard, an AI wrapper, or a banking super app.

The core differentiators are **depth, trust, explainability, and optimization quality** — not the largest card database or the most features.

---

## Engineering philosophy

> **Structured systems first. AI orchestration second.**

The system relies primarily on deterministic logic, normalized reward schemas, explicit calculations, and constrained optimization. LLMs assist with orchestration, summarization, explanation, intent extraction, and recommendation narration — they **do not** calculate reward values, invent transfer ratios, or act as the source of truth.

---

## Project status

**Phase 0 — Product Definition & Architecture.**

| Area | Status |
| --- | --- |
| **Frontend** | Working product-first marketing site (Next.js / Tailwind / shadcn) on a dark/gold design system. Includes a live (mock) Goal Simulator and front-end-only login/signup. |
| **Backend** | Not started — `backend/` is a placeholder. The five engines below are designed but not yet implemented. |
| **Docs** | Active. PRD, architecture, research, UX, and a permanent decision log under [`/docs`](docs/). |

The Goal Simulator currently renders a static mock; it will be wired to the real Simulation Engine once the backend exists. For a live snapshot of what's done / in progress / next, see [`docs/tracker.md`](docs/tracker.md).

---

## MVP scope

The MVP is built **narrow and deep**, centered on **Singapore Airlines business-class optimization using Indian credit cards** and the **KrisFlyer** transfer ecosystem.

**Initial supported cards:** HDFC Infinia · HDFC Diners Black · HDFC Regalia Gold · HSBC TravelOne · Axis Atlas · Axis Magnus · Amex Platinum Travel · SBI Cashback.

**Deliberately out of scope for now:** browser extensions, automatic spend tracking, OCR/SMS parsing, autonomous agents, full airline ecosystem support, every Indian card, mobile apps, financial aggregation, and generic chatbot experiences.

---

## Architecture

The backend is organized around five engines:

1. **Reward Knowledge Engine** — card data, reward rules, transfer ratios, milestones, caps, exclusions. *(The most important system.)*
2. **Reward Valuation Engine** — reward/transfer value estimation, redemption calculations, efficiency scoring.
3. **Optimization Engine** — spend allocation, card strategy generation, reward maximization (heuristic-first).
4. **Simulation Engine** — reward accumulation projection, timeline simulation, milestone tracking, redemption readiness.
5. **AI Reasoning Layer** — intent extraction, explainable outputs, strategy narration — *never* direct reward calculations.

---

## Tech stack

**Frontend:** Next.js · Tailwind CSS · shadcn/ui · Framer Motion
**Backend (planned):** FastAPI · Python
**Database (planned):** Supabase · PostgreSQL
**AI layer (planned):** OpenAI / Gemini · LangGraph · PydanticAI
**Optimization (planned):** OR-Tools · NetworkX
**Scraping (planned):** Playwright · BeautifulSoup

---

## Repository layout

```
OptiMiles/
├── frontend/        Next.js marketing site + Goal Simulator (working)
├── backend/         Placeholder — engines not yet implemented
├── docs/            PRD, architecture, research, UX, decisions, tracker
├── requirements.txt Python deps (backend, currently empty)
└── CLAUDE.md        Project context & engineering constitution
```

---

## Getting started

### Frontend

> **Note:** This project pins recent, fast-moving versions of Next.js (16) and React (19). See [`frontend/AGENTS.md`](frontend/AGENTS.md) — some APIs differ from older releases.

```bash
cd frontend
npm install
npm run dev      # http://localhost:3000
```

Other scripts: `npm run build`, `npm run start`, `npm run lint`.

### Backend

Not yet implemented. When it lands, it will be a FastAPI app wired to Supabase/Postgres. Python dependencies will be tracked in `requirements.txt`.

---

## Documentation

> *Chats are temporary. Documentation is permanent.*

| Path | Contents |
| --- | --- |
| [`docs/prd/`](docs/prd/) | Product requirements |
| [`docs/architecture/`](docs/architecture/) | System & DB schema design |
| [`docs/research/`](docs/research/) | Reward ecosystem & transfer-partner research |
| [`docs/ux/`](docs/ux/) | UX flows |
| [`docs/decisions/`](docs/decisions/) | Permanent decision log (why things were done) |
| [`docs/tracker.md`](docs/tracker.md) | Living snapshot of current project state |
| [`CLAUDE.md`](CLAUDE.md) | Engineering constitution & project context |

---

## License

Proprietary — all rights reserved (no license granted at this time).
