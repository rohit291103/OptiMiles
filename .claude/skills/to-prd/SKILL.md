---
name: to-prd
description: Converts a conversation, decision, or rough feature idea into a properly-shaped PRD saved to docs/prd/, matching the structure of mvp_scope_1.md and the Prompting Standards in root CLAUDE.md. Use when the user says "write this up as a PRD," "turn this into a spec," or asks what a feature's scope/requirements should be before building it.
---

# to-prd

Root `CLAUDE.md` assigns PRD-writing to "ChatGPT (Product Manager)" in its AI Collaboration Model, but PRDs still need to exist in `docs/prd/` regardless of which AI drafted them — and a rough idea discussed with Claude shouldn't have to bounce to another tool just to get written down. This skill produces a PRD draft in the repo's existing shape; the user reviews/validates it per the Workflow Philosophy ("no AI output becomes production truth without validation") before it's treated as settled scope.

## Before drafting

Read `docs/prd/mvp_scope_1.md` first — it's the existing PRD and the template to match in tone and structure. Also check root `CLAUDE.md`'s MVP Philosophy, Initial MVP Scope, and Explicit MVP Exclusions sections — a new PRD must not silently expand scope past what those sections allow without flagging it.

## PRD shape (match `mvp_scope_1.md`)

```markdown
# PRD — <Feature/Capability Name>

## Goal
<One sentence: what user-facing outcome this enables.>

## Scope
<What's in. Be specific — named cards, named routes, named partners, not "support more cards.">

## Out of scope
<What's explicitly excluded for this pass, and why — usually because CLAUDE.md's Explicit MVP Exclusions already rules it out, or it's a later milestone.>

## Requirements
<Numbered, testable. Each one should be checkable as done/not-done.>

## Dependencies
<What existing system/schema/engine this relies on — name the actual file, e.g. docs/architecture/db-schema-v1.md.>

## Open questions
<Anything that needs a human decision before this is buildable.>
```

## Workflow

1. Extract the goal and scope from the conversation — don't pad with speculative requirements the user didn't ask for.
2. Cross-check scope against CLAUDE.md's MVP Exclusions and Current Development Phase. If the idea conflicts (e.g. it implies OCR/SMS parsing, or broad card support), say so in "Out of scope" rather than quietly omitting it.
3. Save as `docs/prd/<kebab-case-feature-name>-v1.md` (bump `v2` on major revision, per `docs-sync` naming convention — never overwrite a shipped PRD's history).
4. Tell the user it's a draft awaiting their review — don't treat it as approved scope in the same turn it was written.
