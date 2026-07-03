# OptiMiles — AI Collaboration Protocol v1

**Document Path:** `/docs/prompts/ai-collaboration-protocol-v1.md`
**Version:** v1 · **Stage:** Process
**Source:** Mirrored from Notion "OptiMiles — AI Collaboration Protocol" (2026-06-02) on 2026-07-03. Filed under `/prompts` because it governs how AI task prompts are written and routed; the role definitions also appear in root `CLAUDE.md` ("AI Collaboration Model").

---

# Purpose

OptiMiles is built as an AI-native product organization where multiple AI systems collaborate across product management, architecture, research, engineering, UX, and optimization systems — while maintaining consistency, architectural clarity, clean documentation, controlled scope, and high-quality outputs.

# AI role definitions

| System | Role | Owns | Does NOT |
|---|---|---|---|
| **ChatGPT** | Product Manager + Systems Architect | PRDs, architecture decisions, sprint planning, roadmap, UX/system design, orchestration, final synthesis, documentation ownership, AI coordination | — |
| **Claude** | Senior Software Engineer | Backend architecture, implementation planning, schema design, code review, refactoring, scalability analysis, optimization engine structure. Priorities: clean engineering, no overengineering, maintainable systems | Define product direction; change MVP scope; introduce unnecessary pivots |
| **Gemini** | Research Analyst | Reward ecosystem research, transfer partner analysis, airline ecosystem research, market comparisons, structured knowledge extraction | Architecture decisions; product direction changes |

# Documentation rules

> Chats are temporary. Documentation is permanent.

AI outputs must never become the source of truth on their own. All finalized decisions are stored in **Notion** (OptiMiles OS: Vision, PRDs, Architecture, UX, Research, Sprint Notes, AI Prompt Library, Decision Logs, Technical Docs) and **GitHub `/docs`** (`/prd`, `/architecture`, `/research`, `/ux`, `/decisions`, `/prompts`).

# Prompting standards

Every major AI task prompt includes: **TASK · ROLE · PROJECT CONTEXT · OBJECTIVE · REQUIREMENTS · CONSTRAINTS · OUTPUT REQUIREMENTS · SAVE OUTPUT AS · NOTION STRUCTURE** (template: [template.md](template.md)).

Output formatting: structured markdown, headings, explicit assumptions and constraints, no fluff, no vague recommendations, implementation-focused.

# Orchestration rules

**Human-in-the-loop is mandatory.** All outputs must be (1) reviewed, (2) synthesized, (3) validated, (4) documented. No AI output is accepted blindly.

Major decisions must record: rationale, tradeoffs, assumptions, future implications — stored in the decision logs (repo: `docs/decisions/`).

# Architecture principles (as they bind AI work)

Structured systems first, AI orchestration second. The LLM must NOT calculate rewards directly, act as the source of truth, or replace deterministic logic. AI primarily: orchestrates (conversational edge only — see [system-execution-flow-v1.md](../architecture/system-execution-flow-v1.md) §0.2), explains, summarizes, reasons, structures outputs.

Engineering: clean systems, maintainability, deterministic reward logic, modular architecture, explainability. Avoid unnecessary microservices, excessive abstractions, premature scaling, AI-hype architecture.

# MVP guardrails (as of this protocol)

Focus: Singapore Airlines business-class optimization, Indian travel credit cards, reward simulations, transfer partner optimization, explainable strategies.
Exclusions: browser extensions, OCR parsing, automatic spend tracking, autonomous agents, full airline ecosystem, every Indian card, mobile apps.
Phase 0 priorities: MVP definition, reward system modeling, architecture clarity, UX flow design, foundational documentation — not heavy implementation, scaling infrastructure, or advanced agents.
