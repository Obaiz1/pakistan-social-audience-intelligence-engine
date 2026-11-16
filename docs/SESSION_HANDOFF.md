# Session handoff

**Last updated:** 2026-11-16 — Phase 0 DONE; Phases 1–4 partially implemented (backend modules written, not yet committed or tested).

## Resume here
1. Read `docs/PROGRESS.md` (phase table) and `docs/TRACEABILITY_MATRIX.md`.
2. Activate the venv (Python 3.12.15): PowerShell `.\.venv\Scripts\Activate.ps1` · Git Bash `source .venv/Scripts/activate`.
   Recreate if missing: `py -3.12 -m venv .venv` then `pip install -e ".[dev,ml]"` (CPU torch: `pip install torch --index-url https://download.pytorch.org/whl/cpu`).
3. Continue with the first phase not marked DONE.

## Written so far (backend/audienceiq)
constants, config, storage/schema.sql, nlp/{normalize,langid,intent,embeddings}, data/{synthetic,synthetic_text},
analytics/{engagement,stats}, clustering/{candidates,evaluate,profile}; tests/fixtures/multilingual_audit.csv.

## Verified facts
- Synthetic corpus seed 42: 3,000 posts, 33,776 comments, deterministic (re-generation identical).
- Reference labeller vs generator latent need: 85.6 % agreement (circular: same author; audit set is the fairer test).

## Next unfinished tasks
1. Clustering experiment (semantic vs lexical vs hybrid; KMeans sweep + HDBSCAN) → finalize selection per ADR-007.
2. anomalies/detect.py, recommendations/engine.py, services/build.py (bundle → CSV tables), storage loader, API.
3. Frontend (Next.js, Repo B layout), tests, docs, GitHub repo (private), Vercel deploy.
