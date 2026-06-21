---
name: docs-sync
description: Keep OptiMILES's /docs tree aligned with the Documentation Rules in root CLAUDE.md — file a decision-log entry, route new content to the right /docs subfolder, or audit /docs for missing folders, broken naming, or duplicated/stale content. Use when a non-trivial decision was just made, when the user asks to "document this" or "log this decision," or when starting work that should read existing docs first.
---

# docs-sync

OptiMILES's root `CLAUDE.md` is explicit: **"Chats are temporary. Documentation is permanent."** This skill is the mechanical half of that rule — it doesn't decide what's worth documenting (use judgment, or ask the user), it makes sure that once something is worth documenting, it lands in the right place with the right name.

## Required structure

Per root `CLAUDE.md`'s "Documentation Structure" section, `/docs` must contain:

```
/docs
  /prd          — product requirements, MVP scope
  /architecture — schemas, system design
  /research     — external research (reward ecosystems, transfer partners, airline programs)
  /ux           — design-system baseline, page/flow specs
  /decisions    — decision log (one file per decision or cleanup pass)
  /prompts      — saved AI task prompts using the template below
```

## Before doing any task in this repo

Read the relevant `/docs` subfolder(s) before writing code or making a recommendation — this project's CLAUDE.md explicitly calls this out as current-phase priority ("documentation discipline"). Don't re-derive scope, schema, or card lists from memory when they're already written down in `docs/prd/mvp_scope_1.md` or `docs/architecture/db-schema-v1.md`.

## Mode A — Audit

Run this when asked to "check the docs" or before a large new feature push:

1. Confirm all six subfolders above exist. Create any that are missing (empty folders with no placeholder file are fine — Git won't track them, so add a one-line `README.md` stating the folder's purpose if it needs to exist before its first real doc).
2. Grep each file for exact-duplicate content (a doc pasted into itself twice is a recurring failure mode here — it happened to root `CLAUDE.md` once already). A quick check: split the file in half and diff the halves; large duplicate blocks will show as near-zero diff.
3. Check naming consistency. Going-forward convention:
   - Decisions: `YYYY-MM-DD-short-slug.md`
   - Everything else: `kebab-case-topic-v1.md` (bump `v2`, `v3`, … on major revisions; don't overwrite history)
4. Report findings; don't silently rewrite historical docs without flagging it to the user first (decisions and research docs are a record of what was true at the time — fix structure/naming, not content, unless asked).

## Mode B — File a decision

When a decision just got made (in this conversation or by the user), write `docs/decisions/YYYY-MM-DD-short-slug.md` using this shape:

```markdown
# Decision Log — <Title>

**Date:** YYYY-MM-DD
**Area:** <frontend / backend / architecture / product>

## Context
<Why this came up — the problem or ambiguity.>

## Decisions
<Numbered list. Each decision states what changed and why, not just what.>

## Not done (deferred)
<Anything explicitly out of scope for this pass, and why.>
```

See `docs/decisions/2026-06-21-frontend-mvp-cleanup.md` for a worked example.

## Mode C — Route new content

If unsure which subfolder something belongs in:
- Defines what to build / scope boundaries → `/prd`
- Defines how something is built (schema, system design, API shape) → `/architecture`
- External findings (transfer ratios, award charts, competitor research) → `/research`
- Page/flow/design-system specs → `/ux`
- A choice that was made and why → `/decisions`
- A reusable AI task prompt (per the Prompting Standards in CLAUDE.md) → `/prompts`, using `docs/prompts/template.md`

When a piece of content spans two categories (e.g. a decision that also changes scope), file the full writeup in `/decisions` and add a one-line cross-reference in the other folder's relevant doc rather than duplicating content.
