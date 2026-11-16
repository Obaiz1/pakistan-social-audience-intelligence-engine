# Progress

| Phase | Status | Evidence |
|---|---|---|
| 0 Environment discovery & upstream audit | DONE | `docs/UPSTREAM_AUDIT.md` (both suites re-run), `docs/assignment/PROJECT3_REQUIREMENTS.md` |
| 1 Foundation & architecture | DONE | repo, venv, `pyproject.toml`, `.env.example`, `.gitignore`, ADRs, `/api/v1/health` |
| 2 Normalized datasets & reproducible demo | DONE (synthetic) · observed BLOCKED | `data/synthetic.py`, `storage/schema.sql`, importer, `test_synthetic.py`, `test_storage.py`, `test_importer.py`; observed collector needs owner key (ADR-012) |
| 3 Content & campaign analytics (Q1) | DONE | `analytics/`, `test_engagement.py` |
| 4 Multilingual NLP & comment clustering (Q2/Q4) | DONE | `nlp/`, `clustering/`, exploratory logs, `test_clustering.py`, `test_nlp.py` |
| 5 Anomalies (Q3) | DONE | `anomalies/detect.py`, `test_anomalies.py`, `docs/ANOMALY_METHOD.md` |
| 6 Recommendations (Q5) | DONE | `recommendations/engine.py`, `test_recommendations.py` |
| 7 Frontend | DONE (build/lint/type/unit) · browser QA pending | `frontend/`, `e2e/` |
| 8 QA, evaluation, academic report | IN PROGRESS | waiting for the seed-42 bundle build to fill evaluation numbers |
| 9 Deployment | TODO | `docs/DEPLOYMENT.md` |
| 10 Final regression & handoff | TODO | |

## Environment (verified 2026-11-15)
Windows 11; Git 2.45.2; Python 3.12.15 (uv-managed interpreter, project venv; matches Vercel's default) and 3.14.4 (system); Node 24.14.1; npm 11.11.0; GitHub CLI logged in as `Obaiz1`; Vercel CLI 54.17.1 logged in; Playwright Chromium 1234 installed.

## Repository
https://github.com/Obaiz1/pakistan-social-audience-intelligence-engine (private) · branches `main`, `feat/project3-engine`.

## Risk register (prioritised)
| # | Risk | Impact | Mitigation / status |
|---|---|---|---|
| 1 | No observed data in this build (permission policy refused using another project's key) | Demo is synthetic only | Clear labelling; collector ready for the owner's key (ADR-012) |
| 2 | Synthetic text makes clustering look better than reality | Overclaiming | Audit set, synthetic recovery reported separately, limitations everywhere |
| 3 | Roman Urdu spelling variance; language-driven clusters | Mixed clusters | Normalisation, boilerplate removal, language-invariant model, language-dominance warnings |
| 4 | Vercel Python bundle size | Deploy failure | No torch; pinned slim requirements |
| 5 | No durable hosted store | Hosted imports cannot persist | Read-only demo; preview/validation works hosted; persistence local |
| 6 | YouTube 30-day policy | Stale observed data | `expires_at` enforced by the API |
