---
name: to-issues
description: Breaks a PRD or decision doc into independently-buildable, vertical-slice work items. Use when the user asks to "break this down," "make a task list," or "turn this into issues" after a PRD or decision has been written.
---

# to-issues

A PRD describes what to build; this skill decides the order and slicing of how to build it without losing the "narrow and deep" MVP philosophy — each item should be a complete, demoable vertical slice (touches schema → logic → UI as needed for that one capability), not a horizontal layer (e.g. not "build all schemas" as one item).

## Before slicing

Read the source PRD/decision doc in full. If it references a schema, also read `docs/architecture/db-schema-v1.md` so slices don't get ordered ahead of their dependencies (e.g. don't slice "spend routing UI" before "card reward-rule schema" exists).

## What makes a good slice

- Independently buildable and testable — a reviewer can see it work end-to-end without the next slice existing.
- Sized to one sitting of focused work, not a multi-day epic.
- Named as an outcome, not a layer: "Show KrisFlyer transfer ratio on card detail" not "Add transfer ratio field."
- Ordered by dependency, not by perceived importance — schema/engine slices that others depend on come first.

## Output

There's no issue tracker or GitHub remote wired up yet (project root isn't even a git repo as of this writing) — so output is a checklist appended to the source doc or saved alongside it, not a `gh issue create` call. If a GitHub remote exists by the time this runs, confirm with the user before creating real issues; default to the checklist doc.

```markdown
## Implementation slices — <source PRD/decision name>

1. [ ] <Outcome-named slice> — depends on: <none | slice N>
   - Touches: <files/schema/engine>
2. [ ] ...
```

Save under the same `/docs` subfolder as the source doc (e.g. a PRD's slice list lives next to it in `docs/prd/`), not in a new location.
