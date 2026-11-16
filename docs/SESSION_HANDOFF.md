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

## Owner actions (BLOCKED items)
- **Observed YouTube data:** snapshot `observed-youtube-20261116` is shipped (expires 2026-12-16). To refresh it and populate comment
  dates: set `YOUTUBE_API_KEY`, run `python pipelines/collect_youtube.py --months 24`, then `python pipelines/report_evaluation.py observed-youtube-<date>`,
  commit and redeploy. **Delete `data/observed/private/2026-11-16/` (raw comment text) by 2026-12-16.**
- **Repository visibility:** private. To share with the instructor:
  `gh repo edit Obaiz1/pakistan-social-audience-intelligence-engine --visibility public --accept-visibility-change-consequences`.
- **Licence:** none chosen (owner decision; upstream repos have none either).
- **Persistent hosted imports (optional):** attach a durable database and implement the user store on it; until then imports persist only locally.
- **Optional AI wording:** local only — `NVIDIA_API_KEY=… AUDIENCEIQ_ENABLE_LLM=1` (model via `NVIDIA_MODEL`).
