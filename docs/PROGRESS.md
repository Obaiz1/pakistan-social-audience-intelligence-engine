# Progress

| Phase | Status | Evidence |
|---|---|---|
| 0 Environment discovery & upstream audit | DONE | `docs/UPSTREAM_AUDIT.md`, `docs/assignment/PROJECT3_REQUIREMENTS.md`, `docs/TRACEABILITY_MATRIX.md` |
| 1 Foundation & architecture | IN PROGRESS | |
| 2 Normalized datasets & reproducible demo | TODO | |
| 3 Content & campaign analytics (Q1) | TODO | |
| 4 Multilingual NLP & comment clustering (Q2/Q4) | TODO | |
| 5 Anomalies (Q3) | TODO | |
| 6 Recommendations (Q5) | TODO | |
| 7 Frontend | TODO | |
| 8 QA, evaluation, academic report | TODO | |
| 9 Deployment | TODO | |
| 10 Final regression & handoff | TODO | |

## Environment (verified 2026-11-15)
Windows 11; Git 2.45.2; Python 3.12.15 (uv-managed interpreter, used for the project venv to match Vercel's default) and 3.14.4 (system); Node 24.14.1; npm 11.11.0; GitHub CLI logged in as `Obaiz1` (scopes `repo`, `gist`, `read:org`); Vercel CLI 54.17.1 logged in; Playwright Chromium builds 1228/1248 cached.

## Risk register (prioritised)
| # | Risk | Impact | Mitigation |
|---|---|---|---|
| 1 | Observed comments are sparse (Repo A audit: ~900 comments / ~2,200 videos) | Observed clusters small | Report exact counts; synthetic classroom corpus carries the demo, clearly labelled |
| 2 | YouTube 30-day refresh/delete policy | Hosted observed data goes stale | Enforced `expires_at`; text never shipped; refresh workflow documented |
| 3 | Vercel Python bundle size (500 MB) | Deploy failure | No torch on Vercel; precomputed artifacts; lexical runtime clustering |
| 4 | Synthetic data makes clustering look better than reality | Overclaiming | ADR-007: synthetic ground-truth recovery reported separately; independent audit set; limitations section |
| 5 | Roman Urdu spelling variance weakens multilingual embeddings | Mixed clusters | Normalisation + hybrid (semantic + char n-gram) candidate, evaluated |
| 6 | No durable hosted store | Hosted imports cannot persist | Read-only public demo; preview/validate works hosted; persistence locally |
