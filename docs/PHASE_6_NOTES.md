# Phase 6 — RAG Pipeline: Implementation Notes

## The honest headline for this phase

This is the first phase where the core deliverable requires libraries (LangChain, sentence-transformers, Qdrant) that genuinely cannot be installed in my sandbox — they need network access for large downloads (sentence-transformers pulls in PyTorch), and I have neither. Everything in this phase was **written correctly against real, known library APIs**, and I did real, executable verification of the parts that don't require those libraries — but the actual embedding generation and Qdrant read/write have not been run by me, only by you, once you have the dependencies installed.

## What was added

- **`backend/scripts/ingest_policies.py`** — the full ingestion pipeline: load (PDF via LangChain's `PyPDFLoader`, falling back to raw `pypdf` if the LangChain package isn't installed; markdown via section-header splitting) → clean → chunk (`RecursiveCharacterTextSplitter`, with a pure-Python fallback) → embed (`sentence-transformers`, model `all-MiniLM-L6-v2`) → upsert into Qdrant (local file-backed mode via `QdrantClient(path=...)`, no separate server process needed) → `PolicyDocument`/`PolicyChunk` rows updated with real metadata. Repeatable: re-running it for an unchanged document is safe (existing chunks/points for that document are replaced, not duplicated).
- **`backend/app/services/rag_service.py`** — query-time retrieval (`retrieve_policy_evidence(query, top_k)`), with a `rag_status()` health check and **graceful degradation everywhere**: if the ML packages aren't installed or the index hasn't been built yet, retrieval returns `[]` rather than raising, consistent with Phase 22's "insufficient policy evidence" principle.
- **`backend/app/routes/policies.py`** (new blueprint) — `GET /policies` (list corpus documents + indexing status, any authenticated user), `GET /policies/rag-status` (health check), `POST /policies/search` (admin-only, manual retrieval test).
- **`requirements.txt`** — added the 4 new packages, called out separately with a comment since they're a meaningfully large install (PyTorch).

## The most important decision this phase: RAG is NOT wired into the live chat flow yet

`retrieve_policy_evidence()` exists and is reachable via `/policies/search`, but `chat.py` still uses Phase 5's static `_policy_evidence_for()` lookup table for the governance response. This was deliberate, not an oversight:

- Phase 5's static lookup is **verified working** (real executable tests passed, matches the capstone brief's worked example exactly).
- RAG retrieval is **completely unexecuted** in this environment — I have never actually run the embedding model or queried Qdrant, because I can't install either here.
- Swapping a tested, working piece of the live governed-chat path for something I've never run once would directly violate "never replace working functionality unnecessarily" and "test after every phase."

**The natural next step, once you confirm ingestion + retrieval actually work on your machine**, is to wire `retrieve_policy_evidence()` into `chat.py` either alongside or in place of the static lookup — and at that point I'd recommend having it *replace* the static table rather than run alongside it (see Phase 5 notes on why two disagreeing evidence sources would be confusing). That's a small, well-scoped follow-up once this phase is confirmed working, not something to do blind now.

## What I actually verified vs. what I couldn't

**Verified for real, against the actual corpus**: I extracted text from all 3 real NIST PDFs and all 4 markdown org policies using `pypdf` (which is available in this sandbox) and ran the exact chunking algorithm the shipped script uses as its fallback path. Results: 696 chunks from the AI RMF Playbook (147 pages, 0 extraction failures), 219 from NIST AI 100-1, 317 from NIST.AI.600-1, and 18–20 chunks per org policy document — **1,306 chunks total** from the current 7-document corpus. I spot-checked extracted text quality directly (page 11 of NIST AI 100-1) and it's clean, readable prose, not garbled OCR-type output. This gives me real confidence in the load → clean → chunk → metadata portion of the pipeline.

**Not verified — genuinely untested**: embedding generation (`sentence-transformers` isn't installed anywhere I have access to), Qdrant collection creation/upsert/search (`qdrant-client` isn't installed either), and therefore retrieval quality/relevance is completely unknown until you run it. The LangChain-specific code paths (`PyPDFLoader`, `RecursiveCharacterTextSplitter`) are written against their real, documented APIs from my training knowledge, but I have not executed them even once — only their fallback paths (which don't use LangChain at all) have been run.

**Please run:**
```bash
cd backend
pip install -r requirements.txt   # this will take a while -- sentence-transformers pulls in torch
python scripts/ingest_policies.py
# Expect: "Indexed <file>: N chunks" for all 7 documents, ending in
# "Ingestion complete. Qdrant collection 'secureai_policy_chunks' at .../qdrant_data"
```
Then, with the backend running:
```bash
curl -X POST http://localhost:5001/api/policies/search \
  -H "Authorization: Bearer <admin_token>" -H "Content-Type: application/json" \
  -d '{"query": "can an intern see employee salary information"}'
```
I'd genuinely like to see this output before deciding whether to wire retrieval into the live chat — if the top results are the Role & Access Control Policy and Data Privacy & Classification Policy sections about salary, that's a strong signal it's working well; if they're not, something in chunking/embedding needs adjustment before it goes anywhere near the governed chat response.

## Also worth knowing

- The `--reset` flag on the ingestion script wipes `PolicyDocument`/`PolicyChunk` rows and the Qdrant collection entirely before rebuilding — useful once you add the 3 remaining external framework PDFs (NIST Privacy Framework, OWASP GenAI Top 10, DPDP Act 2023) to `backend/policy_corpus/external_frameworks/`, since re-running without `--reset` also works (it only replaces the specific document(s) it finds, so adding new files and re-running without `--reset` is the normal, safe workflow).
- `KNOWN_DOCUMENTS` in the ingestion script already has entries pre-filled for those 3 not-yet-uploaded files, using the exact filenames I'd expect (`NIST Privacy Framework.pdf`, `OWASP GenAI Top 10.pdf`, `India DPDP Act 2023.pdf`) — if you name the files differently when you upload them, either rename them to match or let me know the names and I'll update the mapping.
