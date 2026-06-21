---
name: handoff
description: Compresses the current conversation's work and decisions into a structured handoff note for another collaborator (ChatGPT, Gemini, a teammate, or a future Claude session), using the existing docs/prompts/template.md shape. Use when the user says "hand this off to ChatGPT/Gemini," "summarize this for the team," or is about to switch tools/people mid-task.
---

# handoff

Root `CLAUDE.md`'s Documentation Rules are explicit: "Chats are temporary. Documentation is permanent." Its AI Collaboration Model also splits work across three different AI tools (ChatGPT = PM/Architect, Claude = Senior Engineer, Gemini = Research Analyst) — work routinely needs to cross that boundary without losing context. This skill is the mechanical step that makes a chat's content survive the handoff.

## Workflow

1. Read `docs/tracker.md` (via the `tracker-sync` skill) first — the handoff's PROJECT CONTEXT should reflect actual current state, not what the conversation assumed at its start.
2. Identify the destination: which collaborator (ChatGPT, Claude, Gemini, a human teammate) and which `/docs` subfolder their output should ultimately land in, per CLAUDE.md's AI Collaboration Model.
3. Fill out `docs/prompts/template.md`'s shape — don't invent a different structure:
   - **ROLE** — the destination collaborator's role per the AI Collaboration Model (e.g. Gemini = Research Analyst).
   - **PROJECT CONTEXT** — only what's needed to pick up the thread; don't re-paste the whole CLAUDE.md, reference it.
   - **OBJECTIVE** — the specific next action, not the whole project goal.
   - **REQUIREMENTS / CONSTRAINTS** — anything decided in this conversation that the next collaborator must not re-litigate (already-settled scope, already-rejected approaches, and why).
   - **OUTPUT REQUIREMENTS / SAVE OUTPUT AS / NOTION LOCATION / NOTION STRUCTURE** — where their output should land.
4. Save the filled template as `docs/prompts/<date>-<short-slug>.md` so it's retrievable later, and surface it to the user to copy into the other tool — this skill doesn't call external AI APIs itself.

## What belongs in the handoff vs. what doesn't

- Include: decisions already made (and why — a decision without its reasoning gets re-debated), open questions the next collaborator needs to resolve, exact file paths touched so far.
- Exclude: blow-by-blow narration of the conversation, anything already permanently recorded in `/docs` (link to it instead of repeating it).
