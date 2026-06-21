# AI Task Prompt Template

Per CLAUDE.md's Prompting Standards — every important AI task prompt (ChatGPT, Claude, or Gemini) should be written against this template before being run, and the filled-in prompt + output saved alongside the relevant `/docs` entry it produced.

---

```
## ROLE


## PROJECT CONTEXT


## OBJECTIVE


## REQUIREMENTS


## CONSTRAINTS


## OUTPUT REQUIREMENTS


## SAVE OUTPUT AS


## NOTION LOCATION


## NOTION STRUCTURE

```

---

## Usage notes

- **ROLE** — which collaborator is acting (ChatGPT = PM/Architect, Claude = Senior Engineer/Backend Architect, Gemini = Research Analyst), per CLAUDE.md's AI Collaboration Model.
- **SAVE OUTPUT AS** — the `/docs` subfolder + filename the validated output lands in (`/prd`, `/architecture`, `/research`, `/ux`, `/decisions`, `/prompts`).
- Per the Workflow Philosophy, no AI output here becomes production truth until it's been reviewed, synthesized, and validated by a human.
