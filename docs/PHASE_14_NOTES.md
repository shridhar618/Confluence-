# Phase 14 — Policy Management: Implementation Notes

## What was added

**A real gap fixed first**: `scripts/ingest_policies.py` never stored `file_path` on `PolicyDocument`, which would have made a per-document "Re-index" action impossible (nothing to locate the source file from). Fixed by storing it at ingestion time, and refactored the per-document ingestion logic out of the script's main loop into a standalone `ingest_one_document()` function so the CLI script and the new admin API share one implementation rather than two that could drift apart.

**`backend/app/routes/policies.py`** — four new endpoints, all gated by `require_permission("manage_policies")`:
- `GET /policies/<id>/chunks` — the "View" action, lets an admin see exactly what got indexed
- `PUT /policies/<id>/status` — "Disable"/"Enable"
- `DELETE /policies/<id>` — deletes the document and its chunks (cascade), and attempts to clean up the corresponding Qdrant vectors
- `POST /policies/<id>/reindex` — "Re-index", reusing `ingest_one_document()`. Returns a clean 503 with a status breakdown if `sentence-transformers`/`qdrant-client` aren't installed, rather than a stack trace.

**`frontend/src/pages/PolicySourcesPage.jsx`** (new) — document table (Document/Category/Version/Status/Chunks/Last Indexed) with the four actions as icon buttons, plus a slide-in drawer showing indexed chunk content for the "View" action. Shows a warning banner if the RAG dependencies aren't installed in the running environment. Registered at `/policy-sources`, gated by the `manage_policies` permission (not just `adminOnly`), and placed in the sidebar's AI Governance section per the brief's nav structure.

## A real gap found and fixed, not just documented

While writing the disable-action docstring, I stated a caveat ("retrieval doesn't filter on document status yet") — then, per the habit from Phase 11's icon mistake, actually went and checked `rag_service.retrieve_policy_evidence()` before shipping that caveat as a permanent limitation. It genuinely didn't filter. I fixed it directly: retrieval now skips any chunk whose document `status != "active"`, verified with a small logic test covering active, disabled, and orphaned-chunk cases. **Disabling a policy document is now a real, load-bearing action** — it actually removes that document from future governance decisions, not just from an admin's own view of the list.

## Deletion and audit evidence

Deleting a `PolicyDocument` cascades to its `PolicyChunk` rows (existing Phase 1 relationship) and best-effort cleans up the matching Qdrant vectors. If the Qdrant cleanup fails, the SQL rows are already gone — an orphaned vector is harmless (it can never resolve back to real content, since a lookup by `chunk_id` will find nothing), so I log it rather than fail the whole request or roll back a legitimate deletion the admin asked for.

## Verified for real

- Ran the disabled-document filtering logic (`not chunk.document or chunk.document.status != "active"`) against fake stand-ins for active, disabled, and orphaned chunks — all three cases correct.
- Icon check, learned from Phase 11: verified every icon in the new page against what's already proven to work elsewhere in the codebase **before** shipping, not after. Caught one (`FileText`) that wasn't proven and swapped it for `BookOpen` (already used successfully in `ChatPage.jsx`).
- Syntax-checked all new/modified Python and JSX.

## What I could NOT verify

Whether `DELETE .../<id>` actually cascades correctly against real SQLite data, whether the re-index endpoint's dynamic `sys.path` manipulation to import from `scripts/` actually works when Flask is running as a proper package (this is the riskiest part of this phase — dynamically importing a top-level script module from inside a Flask route is unusual enough that I want to flag it explicitly rather than imply confidence I don't have), and whether the frontend page renders and the drawer displays real chunk content.

**Please verify, especially the re-index endpoint**:
```bash
cd backend && pip install -r requirements.txt && python scripts/ingest_policies.py
python app.py
curl http://localhost:5001/api/policies -H "Authorization: Bearer <admin_token>"
curl -X POST http://localhost:5001/api/policies/1/reindex -H "Authorization: Bearer <admin_token>"
# ^ this is the part I'm least confident about -- if it 500s with an import
#   error, the sys.path approach needs to change to a proper package import
curl -X PUT http://localhost:5001/api/policies/1/status -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" -d '{"status": "disabled"}'
curl -X POST http://localhost:5001/api/policies/search -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" -d '{"query": "salary information"}'
# confirm the disabled document's chunks no longer appear in results
```
```bash
cd frontend && npm run build && npm run dev
# visit /policy-sources as admin
```
