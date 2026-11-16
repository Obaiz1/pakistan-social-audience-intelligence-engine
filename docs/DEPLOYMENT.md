# Deployment (Vercel)

## Status: DEPLOYED AND VERIFIED (2026-11-16)
| Item | Value |
|---|---|
| Production URL | **https://audienceiq-pk.vercel.app** (public, read-only demo; synthetic dataset by default + observed YouTube snapshot with comment text withheld) |
| Vercel project | `audienceiq-pk` (team "obaiz-s-projects"), root directory `frontend`, framework Next.js, Node 24.x, source files outside root enabled |
| Deployment | latest: `audienceiq-gxovpqsz2-obaiz-s-projects.vercel.app` (commit `b7e902e`, adds the observed dataset); previous: `dpl_ES6uBNjWCqBQNS28FLE4VyXThB6s` (commit `1d153e2`) — both via the Vercel CLI from the repo root |
| Deployed commit | **`b7e902e`** (reported live by `/api/v1/health → build_commit`; later commits change docs/evidence only) |
| Production env (names only) | `AUDIENCEIQ_HOSTED=1`, `APP_ENV=production`, per-deployment `AUDIENCEIQ_BUILD_COMMIT`; **no secrets** |
| Storage | committed CSV bundle → in-memory SQLite per function instance (read-only); no database attached |

### Production verification (actual requests, 2026-11-16)
| Check | Result |
|---|---|
| `GET /api/v1/health` | `status: ok`, `environment: production`, `hosted: true`, `writes_enabled: false`, `datasets: 1`, `problems: []` |
| 18 API routes (datasets, options, analytics ×3, clusters, cluster detail, evaluation, comments, anomalies, recommendations, posts, quality, methodology, PDF/XLSX/CSV export, template) | all **200**; 0.4–1.2 s warm; XLSX export (3.0 MB) 12.7 s |
| 10 page routes | all **200**; unknown route 404 |
| Writes on the public demo (`/imports/confirm`, `/datasets/demo`, `DELETE /datasets/…`) | **403** with an explanatory message |
| Cross-site POST (`Origin: https://evil.example`) | **403**; same-origin CSV preview returns validation results (422) |
| Browser journey `APP_URL=https://audienceiq-pk.vercel.app QA_TAG=prod node frontend/e2e/journey.mjs` | **12/12**, 0 console errors, 0 API errors (`docs/evidence/e2e-journey-prod.json`) |
| Visual/accessibility sweep `… node frontend/e2e/screens.mjs` | **40/40** (10 routes × 375/1440 × dark/light) (`docs/evidence/qa-screens-prod.json`, `docs/screenshots/prod/`) |
| Secrets | none configured; `.env.local` created by `vercel link` (OIDC token) deleted locally, never committed |
| Redeploy with observed dataset (commit `b7e902e`) | health `ok`, `datasets: 2`; observed dataset: 10 API routes 200, every `comment_text` null with `text_visible: false`; journey **12/12**; observed visual sweep **40/40** (`docs/evidence/qa-screens-prod-observed.json`) |

## Provider constraints (checked 2026-11-15 against vercel.com/docs)
Python 3.12 is the default runtime (3.13/3.14 available); Python function bundles may be up to 500 MB uncompressed; Hobby functions run up to 300 s with 2 GB memory; request/response bodies are limited to 4.5 MB; the function filesystem is not durable storage. Consequences: no torch on Vercel (embeddings precomputed), uploads capped at 2 MB, hosted mode is read-only.

## Project layout on Vercel
- Root directory: `frontend` (Next.js framework preset), Node 24.
- `frontend/vercel.json`: Python function `api/index.py` (maxDuration 60 s, `includeFiles: .backend/**`), rewrite `/api/v1/:path*` → `/api/index`.
- `npm run build` = `node scripts/prepare-backend.mjs && next build`; the script copies `backend/audienceiq/` and `data/datasets/` into the git-ignored `frontend/.backend/`, which the Python function imports.
- Python dependencies: `frontend/requirements.txt` (pinned; no ML extras). Python version: `frontend/.python-version` (3.12).
- "Include source files outside the root directory" must be enabled so the build can read `../backend` and `../data` (CLI deploys from the repo root upload them).

## Environment variables (names only)
| Name | Value | Why |
|---|---|---|
| `AUDIENCEIQ_HOSTED` | `1` | read-only public demo (also implied by Vercel's `VERCEL=1`) |
| `APP_ENV` | `production` | shown by `/api/v1/health` |
| `VERCEL_SUPPORT_LARGE_FUNCTIONS` | not needed unless the bundle exceeds 500 MB | |
No secrets are required. Do **not** set `AUDIENCEIQ_ALLOW_WRITES` without a durable database.

## Deploy with the CLI
```bash
cd <repo root>
vercel link --project audienceiq-pk          # first time; root directory = frontend
vercel env add AUDIENCEIQ_HOSTED production   # value 1
vercel deploy --prod
```

## Smoke test (run against the production URL)
```bash
curl -s https://<url>/api/v1/health
APP_URL=https://<url> QA_TAG=prod node frontend/e2e/journey.mjs
APP_URL=https://<url> QA_TAG=prod node frontend/e2e/screens.mjs
```
(Git Bash on Windows: prefix with `MSYS_NO_PATHCONV=1` if paths get rewritten.)

## Rollback
`vercel ls audienceiq-pk` → `vercel promote <previous-deployment-url>` (or `vercel rollback`). Data is immutable per deployment (committed bundles), so a rollback also restores the previous dataset.

## Persistent hosted imports (not configured)
Would require a durable store (e.g. Neon Postgres through the Vercel marketplace) and an implementation of the user store on Postgres; until then imports persist only in local mode.

## Troubleshooting
- `/api/v1/*` returns 404 on Vercel → check the rewrite in `frontend/vercel.json` and that `api/index.py` exists in the deployment.
- 500 on cold start mentioning `data/datasets` → `prepare-backend.mjs` did not run or `data/datasets` was not uploaded (enable files outside root).
- Bundle too large → confirm `frontend/requirements.txt` has no torch/sentence-transformers.
