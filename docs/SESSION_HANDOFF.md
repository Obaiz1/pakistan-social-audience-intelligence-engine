# Session handoff

**Last updated:** 2026-11-16 — backend + frontend implemented and committed; seed-42 bundle build in progress; deployment not yet done.

## Resume here
1. Read `docs/PROGRESS.md` and `docs/TRACEABILITY_MATRIX.md`.
2. Venv (Python 3.12.15): PowerShell `.\.venv\Scripts\Activate.ps1` · Git Bash `source .venv/Scripts/activate`.
   Recreate: `py -3.12 -m venv .venv; pip install -e ".[dev]"`; ML extra: `pip install torch --index-url https://download.pytorch.org/whl/cpu; pip install -e ".[ml]" umap-learn`.
3. Frontend: `npm --prefix frontend ci`.

## If the dataset bundle is missing (`data/datasets/synthetic-lawn-demo-v1/`)
`python pipelines/build_demo.py` (≈15–20 min CPU; mpnet embeddings are cached in `data/cache/embeddings/` once computed).

## Next unfinished tasks
1. Fill evaluation numbers: `docs/CLUSTERING_EVALUATION.md`, `docs/DATA_PROVENANCE.md`, `docs/PROJECT3_FINAL_REPORT.md`, README `{{TBD_*}}` markers (grep before committing).
2. Local browser QA: `uvicorn audienceiq.api.app:app --app-dir backend --port 8000` + `npm --prefix frontend run build && npx --prefix frontend next start -p 3000`, then `node frontend/e2e/journey.mjs` and `node frontend/e2e/screens.mjs`.
3. Commit bundle + docs; push; open PR `feat/project3-engine` → `main`.
4. Vercel: `vercel link` (root `frontend`), `vercel deploy --prod`, run e2e against the production URL, fill `docs/DEPLOYMENT.md`.

## Blocked (owner action)
- Observed YouTube data: run `pipelines/collect_youtube.py` with your own `YOUTUBE_API_KEY` in the environment.
- Repository visibility: private; make public for grading with `gh repo edit Obaiz1/pakistan-social-audience-intelligence-engine --visibility public --accept-visibility-change-consequences`.
