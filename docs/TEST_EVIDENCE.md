# Test evidence

Commands were executed on Windows 11 (Python 3.12.15 venv, Node 24.14.1) unless stated otherwise. Results are copied from the actual runs; nothing here is a projected result.

## Upstream repositories (Phase 0, 2026-11-15)
| Command | Result |
|---|---|
| Repo A `python -m pytest -q -p no:cacheprovider` | 122 passed, exit 0 |
| Repo B `python -m pytest -q -p no:cacheprovider` | 200 passed, 8 failed, 3 skipped, exit 1 (Windows-specific: file locks, POSIX modes, symlink privilege, `os.killpg`) |

## Backend (Project 3)
| Date | Command | Result |
|---|---|---|
| 2026-11-16 | `python -m pytest -q` | 98 passed (first full run; 1 PDF-export failure fixed beforehand — fpdf2 cursor position) |
| 2026-11-16 | `python -m ruff check backend pipelines` | All checks passed |
| 2026-11-16 | `python -m pytest -q` (after concurrency fix, gloss, wording module) | **102 passed** |

## Frontend
| Date | Command | Result |
|---|---|---|
| 2026-11-16 | `npx tsc --noEmit` | exit 0 |
| 2026-11-16 | `npx eslint .` | exit 0 (after fixing one `react-hooks/refs` error in `lib/api.ts`) |
| 2026-11-16 | `npx vitest run` | 2 files, 9 tests passed |
| 2026-11-16 | `npx next build` | compiled; 11 routes prerendered (static shells) |

## Dataset build
| Date | Command | Result |
|---|---|---|
| 2026-11-16 | `python pipelines/build_demo.py` (without gloss) | exit 0, 965 s; selected semantic KMeans k=8; audit 18 %; superseded (ADR-013) |
| 2026-11-16 | `python pipelines/build_demo.py` (with Roman-Urdu gloss) | exit 0, 767 s; 3,000 posts / 33,776 comments; selected semantic KMeans k=8; synthetic need NMI 0.429; audit 52 %; anomaly recall 53 % |
| 2026-11-16 | `refresh_recommendations()` (wording/priority fix) | 18 cards; `verify_manifest` → [] |
| 2026-11-16 | `python pipelines/report_evaluation.py` | wrote CLUSTERING_EVALUATION.md, DATA_PROVENANCE.md |

## Observed collection (2026-11-16, owner-authorised)
| Command | Result |
|---|---|
| `python pipelines/collect_youtube.py --months 24 --env-file <owner's Project 1 .env>` | exit 0: 2,165 videos, 809 comments, 663 quota units, 180 s; bundle `observed-youtube-20261116` (KMeans k = 4) |
| inspection | comment_text non-null 0, exemplar text non-null 0 (withheld OK); **bug: comment dates all null**, adapter fixed + `test_youtube_adapter.py` (3 tests) |
| second collection to repopulate dates | refused by the permission policy (not retried) |
| API on observed dataset (12 routes + 3 exports) | all 200; text null with withheld notice; quality checks all pass |
| `QA_DATASET=observed-youtube-20261116 node e2e/screens.mjs` | **40/40** (`docs/evidence/qa-screens-local-observed.json`) |
| `python -m pytest -q` | **105 passed** |

## Browser QA (local production build: `npm run build` + `next start`, API on the real bundle)
| Date | Command | Result |
|---|---|---|
| 2026-11-16 | `node e2e/journey.mjs` (smoke bundle) | 11/12 → fixed a test race → 12/12 |
| 2026-11-16 | `node e2e/screens.mjs` (smoke bundle) | 39/40: one API 500 on `/api/v1/datasets` → **real bug** (shared SQLite `row_factory` race under concurrent requests) fixed + regression test → 40/40 |
| 2026-11-16 | `APP_URL=http://127.0.0.1:3000 QA_TAG=local node e2e/journey.mjs` | **12/12 passed, 0 console errors, 0 API errors** — `docs/evidence/e2e-journey-local.json` |
| 2026-11-16 | `APP_URL=http://127.0.0.1:3000 QA_TAG=local node e2e/screens.mjs` | **40/40** (10 routes × 375/1440 px × dark/light: HTTP 200, h1 present, no horizontal overflow, all controls named, no console errors) — `docs/evidence/qa-screens-local.json`, screenshots `docs/screenshots/local/` |

Visual review of screenshots led to three UI fixes before the final sweep: mobile-only menu buttons visible on desktop (CSS specificity), cramped mobile top bar, stacked toggle icons.

## GitHub Actions
| Run | Commit | Result |
|---|---|---|
| 43818030768 | 92cdcb8 | failure — expected: dataset bundle not yet committed (frontend build + manifest step) |
| 43823355039 | 1d153e2 | **success** — backend (ruff, compile, manifest verification, pytest), frontend (lint, typecheck, vitest, build), e2e (journey on Linux) |

## Production (https://audienceiq-pk.vercel.app, commit 1d153e2)
| Command | Result |
|---|---|
| curl smoke test of 18 API routes + 10 pages | all 200; writes 403; cross-site 403 (details in `docs/DEPLOYMENT.md`) |
| `APP_URL=https://audienceiq-pk.vercel.app QA_TAG=prod node frontend/e2e/journey.mjs` | 12/12 (first run 12/12 but one check matched the hostname instead of the path — test fixed and re-run: 12/12 with real navigation to `/audience?cluster=1`) |
| `APP_URL=https://audienceiq-pk.vercel.app QA_TAG=prod node frontend/e2e/screens.mjs` | 40/40 |
