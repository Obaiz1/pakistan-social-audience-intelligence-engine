# UI QA report — Editorial Intelligence redesign

All results below were produced in this session against a local production build (`next build` + `next start` on :3000, FastAPI on :8000 serving the committed dataset bundles). Production results are in the section below and in `UI_FINAL_HANDOFF.md`. Raw evidence is in `docs/evidence/`.

## Automated checks
| Check | Command | Result |
|---|---|---|
| Backend tests | `python -m pytest -q` | **109 passed** (105 before + 4 for the new endpoints/fields) |
| Backend lint | `ruff check backend pipelines` | clean |
| Typecheck | `npx tsc --noEmit` | clean |
| Lint | `npx eslint .` | clean |
| Unit tests | `npx vitest run` | **17 passed** (3 files; new: script direction, workflow-status storage, heat-cell contrast cap) |
| Build | `npm run build` | 13 static app routes + not-found (3 new: `/segments`, `/model`, `/reports/brief`) |

## Ten user journeys — `node e2e/journey.mjs`
Result: **11/11 steps (10 journeys + API health), 0 console errors, 0 API errors** — `docs/evidence/e2e-journey-redesign-local.json`.

| # | Journey | What is asserted |
|---|---|---|
| J1 | Overview | Mode banner; exactly five answer cards; KPI card opens its evidence page |
| J2 | Q1 Attention | ≥ 3 content types in the CI table; post drawer opens and closes with Escape; platform filter is written to the URL; the **filtered CSV** link carries the filter and its header contains disclaimer, mode, clustering run and filters |
| J3 | Q2 Needs | Price cluster → Roman-Urdu filter → gloss line visible → linked post drawer → recommended-action link lands on `/recommendations#REC-…` |
| J4 | Q3 Anomaly lab | Ranked-flags panel; drawer shows cohort median baseline and the "not evidence of fraud" caveat; **Tab/Shift+Tab stay inside the modal drawer**; Escape closes |
| J5 | Q4 Segments | Heading, "Unit of analysis: comments" notice, segment cards, compare-by-brand updates URL and renders heat cells |
| J6 | Q5 Action center | Each card has Opportunity / Why it matters / Evidence / Suggested test / Uncertainty; status set to Planned shows a toast and **survives a reload**; an evidence chip navigates to its source screen |
| J7 | Model lab | Audit metric baseline (18 %) stated and the exploratory 46 % explicitly marked "not the shipped figure"; candidate/error/method tables present |
| J8 | Data hub | Source-status panel with platform matrix; no string resembling an API key on the page; collector reported "not configured"; CSV import preview validates without storing |
| J9 | Reports → brief | Export links; brief shows Q1, Q2, Q3, Q4 & Q5 and Limitations; **print media hides the navigation rail**; server PDF returns `application/pdf` |
| J10 | Mobile + keyboard | 390 px: no horizontal scroll, menu opens and navigates; skip link is the first Tab stop; Urdu cells render `dir="rtl" lang="ur"`; comment sort updates URL; theme toggles both ways |

## Screen sweep with axe-core — `node e2e/screens.mjs`
Matrix: 13 routes × {390, 1440} px × {light, dark} with axe-core (WCAG 2.0/2.1 A + AA), plus 4 key screens (`/`, `/audience`, `/segments`, `/recommendations`) at 320, 375, 768 and 1280 px. Each check requires HTTP 200, an `h1`, no horizontal overflow, every control named, no console errors, no API 5xx, and zero serious/critical axe violations.

| Dataset | Result | Evidence |
|---|---|---|
| Synthetic demo (`synthetic-lawn-demo-v1`) | **68/68 clean · axe serious/critical 0 · moderate/minor 0** | `docs/evidence/qa-screens-redesign-local.json`, `docs/screenshots/redesign-local/` |
| Observed YouTube (`observed-youtube-20261116`) | **68/68 clean · axe serious/critical 0 · moderate/minor 0** | `docs/evidence/qa-screens-redesign-local-observed.json`, `docs/screenshots/redesign-local-observed/` |

### What the sweeps found, and what was fixed
The first axe run was **16/68** — the failures were real and are recorded here rather than hidden:

| Finding (axe rule) | Where | Fix |
|---|---|---|
| `color-contrast` 4.37:1 | Accent badges (`P1`, "72 % agree", "selected") in light theme | New `--accent-text` token (#066b62 light / #6fd6c5 dark) for accent text on tinted backgrounds |
| `color-contrast` 4.23:1 | Rail question-range labels | `--rail-muted` darkened to #58636a |
| `color-contrast` 4.28:1 | Banner counts (opacity 0.92) | Opacity removed |
| `color-contrast` 3.1–4.3:1 | Dark-theme heat cells | Dark `--heat` base deepened to `28,120,110` |
| `color-contrast` (observed data only) | Light heat cells at high shares | Shared `heatAlpha()` caps opacity at 0.72 (unit-tested) |
| `label-content-name-mismatch` | KPI links and brand link overrode visible text with `aria-label` | Visible text kept as the name; `sr-only` suffix "open evidence"; brand uses `title` |
| `scrollable-region-focusable` | Horizontally scrollable tables without focusable content | All 33 `.table-wrap` regions are focusable with a visible focus ring |
| Overflow 392 px at 390 | Brief tables | Wrapped in scroll regions |

### Visual review (screenshots read by eye, not only by script)
Fixed after review: rail tagline was cut off (now wraps); pipeline steps were shown alphabetically (now in run order: normalise → enrich → embed → cluster → anomalies → recommendations); mixed comments that begin with an Urdu word flipped the whole line RTL (`unicode-bidi: plaintext` → `isolate`, so a Latin-majority sentence stays LTR); the mobile question stepper showed bare numbers (now shows short labels). The "UMAP/HDBSCAN" wording on the Model lab was checked against the shipped candidate runs (`reducer: umap`) and is accurate.

## Production (https://audienceiq-pk.vercel.app, build `80bf070`)
| Check | Result | Evidence |
|---|---|---|
| 10 journeys + health | **11/11**, 0 console errors, 0 API errors (first run 10/11: two test-timing waits fixed, see handoff) | `docs/evidence/e2e-journey-redesign-prod.json` |
| Screen + axe sweep, synthetic | **68/68**, axe serious/critical 0 | `docs/evidence/qa-screens-redesign-prod.json` |
| Screen + axe sweep, observed | **68/68**, axe serious/critical 0 | `docs/evidence/qa-screens-redesign-prod-observed.json` |
| GitHub Actions on PR #3 | backend, frontend, e2e (journeys + axe sweep) all pass | runs 43842912448, 43842925353 |

## Not covered / limits of this QA
- Browsers: Chromium only (Playwright). Safari and Firefox were not tested.
- Screen readers: semantics were checked by axe and the scripts; no manual NVDA/VoiceOver session was run.
- Workflow status is per-browser `localStorage`; it is not shared between users and is not a server feature.
- Automated contrast checks cover rendered text; chart marks (SVG) are checked by the chart ⇄ table parity instead.
