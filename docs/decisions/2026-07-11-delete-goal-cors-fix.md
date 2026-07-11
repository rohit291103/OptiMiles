# Decision Log — Delete-Goal CORS Preflight Fix

**Date:** 2026-07-11
**Area:** backend (API / CORS)

## Context

The dashboard's "Delete goal" action (`GoalMenu` → `ConfirmDialog` →
`deleteSavedGoal` → `DELETE /goals/{id}`) reportedly "still didn't work" after
the delete UI was built. The frontend flow, the API client
(`deleteSavedGoal`), the endpoint (`goals.delete_goal`), and the repo
(`delete_goal_lineage`, a scoped 4-statement transactional cascade) were all
read and found structurally correct — the delete never actually failed on any
of those layers because it never reached them.

Root cause, found in the live backend log rather than the code:
`OPTIONS /goals/{id}` preflights for the delete were returning **400 Bad
Request**, and **no `DELETE` request ever followed**. The CORS middleware in
`app/main.py` was configured `allow_methods=["GET", "POST"]` — it predated the
delete endpoint. Starlette's `CORSMiddleware` answers a preflight 400 when the
requested method isn't in `allow_methods`, so the browser saw a rejected
preflight and blocked the `DELETE` before sending it. From the frontend that
surfaced as `deleteSavedGoal`'s generic network-error catch, never a real
404/500 — which is why it looked like "nothing happens."

## Decisions

1. **Added `DELETE` to the CORS `allow_methods`** in `app/main.py`
   (`["GET", "POST"]` → `["GET", "POST", "DELETE"]`). One line; the endpoint,
   auth scoping, and cascade were already correct and unchanged. Comment
   updated to record *why* DELETE must be listed (preflight would 400
   otherwise).

Verified live against the reloaded server:
`OPTIONS /goals/{id}` with `Access-Control-Request-Method: DELETE` now returns
`200 OK` and `Access-Control-Allow-Methods: GET, POST, DELETE`, so the browser
will permit the DELETE.

## Not done (deferred)

- **End-to-end browser verification of the delete** (menu → confirm → card
  removed) was attempted via the frontend-reviewer agent but blocked at
  Supabase auth (ES256 tokens can't be forged for a headless session without
  real login). The CORS layer — the actual defect — is verified by the
  preflight response; the UI layers above it were already correct by
  inspection. Left for the user's own logged-in session to confirm.
