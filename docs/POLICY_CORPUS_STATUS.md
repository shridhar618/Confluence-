# Policy Corpus Status (Phase 7 tracking)

This tracks progress toward the full policy corpus that the RAG pipeline (Phase 6) will ingest. Nothing in this document implies the ingestion pipeline exists yet — Qdrant/embeddings/LangChain wiring is still Phase 6, not yet built. This is source-material intake only.

## External frameworks (6 planned)

| # | Source | Status | File |
|---|---|---|---|
| 1 | NIST AI RMF 1.0 | ✅ Received & verified | `policy_corpus/external_frameworks/NIST AI 100-1.pdf` |
| 2 | NIST Generative AI Profile | ✅ Received & verified | `policy_corpus/external_frameworks/NIST.AI.600-1.pdf` |
| 3 | NIST AI RMF Playbook | ✅ Received & verified | `policy_corpus/external_frameworks/AI RMF Playbook.pdf` |
| 4 | NIST Privacy Framework | ⏳ Pending — user will upload | — |
| 5 | OWASP GenAI / LLM Top 10 | ⏳ Pending — user will upload | — |
| 6 | India DPDP Act 2023 | ⏳ Pending — user will upload | — |

Verification method: each received PDF was opened and its title page / early text was read directly (via `pypdf`), not inferred from filename alone, to confirm it's the actual document rather than a mislabeled file.

## Organization-specific policies (4 planned)

| # | Policy | Status | File |
|---|---|---|---|
| 1 | AI Acceptable Use Policy | ✅ Drafted | `policy_corpus/organization/AI_Acceptable_Use_Policy.md` |
| 2 | Role & Access Control Policy | ✅ Drafted | `policy_corpus/organization/Role_and_Access_Control_Policy.md` |
| 3 | Data Privacy & Classification Policy | ✅ Drafted | `policy_corpus/organization/Data_Privacy_and_Classification_Policy.md` |
| 4 | AI Security & Incident Response Policy | ✅ Drafted | `policy_corpus/organization/AI_Security_and_Incident_Response_Policy.md` |

### Drafting notes

- All four org policies are written to be **internally consistent with the Phase 1 schema**: they cite the exact permission names (`view_employee_salary`, `view_employee_pii`, etc.) and role names (Guest/Intern/Software Engineer/HR/Manager/Supervisor/Admin) already seeded in `services/permissions.py` and `services/roles.py`. This matters for Phase 6: when the RAG pipeline retrieves a chunk to justify a governance decision, the chunk's language will actually match the real permission/role names the decision engine used, instead of being generic boilerplate that happens to sound relevant.
- Each policy uses numbered sections/clauses (e.g., "§3.2", "§4.1(b)") specifically so that Phase 6 chunking can preserve a meaningful `section` value per chunk, and the assistant can cite e.g. "Role & Access Control Policy §3.2" rather than just the document title — matching the capstone brief's worked example in Phase 5.
- These are currently `.md` files, not PDFs. The ingestion script (Phase 6) should support both — markdown chunking is simpler and these are the org's own authored documents, not scanned externals, so PDF conversion isn't necessary unless you'd specifically like these as PDFs for presentation purposes.
- Cross-references between the four documents (each ends with a "Related Policies" section) are intentional — the AI Assistant's "Policy Evidence" output in Phase 5's worked example cites more than one document per decision (e.g., both Role & Access Control Policy and Data Privacy & Classification Policy for a salary request), and the RAG retrieval needs multiple genuinely relevant documents to find, not just one.

## Next steps

1. You upload the 3 remaining external framework PDFs (NIST Privacy Framework, OWASP GenAI/LLM Top 10, India DPDP Act 2023) whenever ready — no rush, this doesn't block anything else.
2. Once Phase 1 test results come back clean, we proceed to Phase 2 (RBAC enforcement) before touching Phase 6 (RAG ingestion) — the corpus sitting here is prep, not yet wired into anything.
