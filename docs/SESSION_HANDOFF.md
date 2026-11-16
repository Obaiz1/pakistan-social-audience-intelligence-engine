# Session handoff

**Last updated:** 2026-11-16 — all phases done; production verified at https://audienceiq-pk.vercel.app.

## Resume / rerun
1. Venv (Python 3.12.15): PowerShell `.\.venv\Scripts\Activate.ps1` · Git Bash `source .venv/Scripts/activate`.
   Recreate: `py -3.12 -m venv .venv; pip install -e ".[dev]"`; ML extra (only to rebuild the dataset):
   `pip install torch --index-url https://download.pytorch.org/whl/cpu; pip install -e ".[ml]" umap-learn`.
2. Run locally: `uvicorn audienceiq.api.app:app --app-dir backend --port 8000` and `npm --prefix frontend ci && npm --prefix frontend run dev`.
3. Rebuild dataset: `python pipelines/build_demo.py` (≈13 min) then `python pipelines/report_evaluation.py`.
4. Redeploy: from the repo root `vercel deploy --prod -e AUDIENCEIQ_BUILD_COMMIT=$(git rev-parse --short HEAD)`, then
   `APP_URL=https://audienceiq-pk.vercel.app QA_TAG=prod node frontend/e2e/journey.mjs`.

## Completed on 2026-11-16 (owner-requested)
- Observed YouTube snapshot re-collected with comment dates and deployed (commit `4c0c35f`).
- PR #1 merged into `main` (merge commit `ea7a706`).
- Repository made **public** after a full-history scan (no key patterns, no `.env` files, no observed comment text in any version, noreply author email only).
- Raw observed comment text (`data/observed/private/2026-11-16/`) deleted locally; only the text-withheld bundle remains.

## Remaining owner decisions
- **Observed data expiry:** the snapshot expires 2026-12-16 (the API stops serving it then). To refresh: set `YOUTUBE_API_KEY`,
  run `python pipelines/collect_youtube.py --months 24`, then `python pipelines/report_evaluation.py observed-youtube-<date>`, commit and redeploy;
  delete the new `data/observed/private/<date>/` folder after building.
- **Licence:** none chosen (owner decision; upstream repos have none either).
- **Persistent hosted imports (optional):** attach a durable database and implement the user store on it; until then imports persist only locally.
- **Optional AI wording:** local only — `NVIDIA_API_KEY=… AUDIENCEIQ_ENABLE_LLM=1` (model via `NVIDIA_MODEL`).
