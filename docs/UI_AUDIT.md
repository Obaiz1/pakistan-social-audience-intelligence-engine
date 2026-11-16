# UI audit (Phase 0 of the frontend redesign brief, 2026-11-16)

## Verified baseline (not owner-reported — checked in this session)
| Item | Verified state |
|---|---|
| Repo | `Obaiz1/pakistan-social-audience-intelligence-engine`, **public**, `main` @ `c9824d3`, clean; work continues on `feat/ui-editorial-redesign` |
| Backend tests | `python -m pytest -q` → **105 passed** (includes the catalogue-concurrency regression test) |
| Frontend | `tsc --noEmit` ok · `eslint .` ok · `vitest run` 9 passed · `npm run build` ok (last run) |
| Deployment | **Deployed**: https://audienceiq-pk.vercel.app, `/api/v1/health` 200 (the brief's "not yet deployed" is outdated) |
| Data | Synthetic seed-42 corpus (3,000 posts / 33,776 comments) **and** an observed YouTube snapshot (2,165 videos / 809 comments, text withheld, expires 2026-12-16). The brief's "YouTube blocked" is outdated |
| ADR-013 metric | The "18 % → 46 %" figure was an exploration number. The *shipped* metric is **audit cluster-name accuracy**: share of 100 hand-labelled audit comments whose nearest cluster's post-hoc need equals the human label — **18 % (no gloss) → 52 % (with gloss)** in the final builds. It is not model accuracy on real data |
| `frontend-design` plugin | Present in the plugin marketplace directory but **not installed**; installing needs the interactive `/plugin install frontend-design@claude-plugins-official`, which cannot run in this session. The brief's written design specification is followed instead; the plugin is **not** claimed to have run |
| Playwright | Local `playwright@1.62.1` + Chromium 1234 (scripts in `frontend/e2e/`); no Playwright plugin |

## Route inventory (existing — all must keep working)
| Route | Purpose | Q | Notes / gaps vs brief |
|---|---|---|---|
| `/` | Overview | Q1–Q5 | Needs hero is a list, not the main visual; no pipeline-status card; KPI cards don't click through |
| `/content` | Content performance | Q1 | No filtered CSV download on the page (only on /reports) |
| `/audience` | Cluster explorer | Q2/Q4 | No gloss shown as supporting info; linked posts only as IDs; no explicit mixed/noise/ADR-013 callout |
| `/comments` | Comment explorer | Q2 | No sort; Urdu excerpts use `unicode-bidi` but not `dir="rtl"` |
| `/anomalies` | Anomaly list + drawer | Q3 | No ranked score chart; no "broader cohort" baseline-quality warning |
| `/campaigns` | Campaign comparison | Q1/Q4 | OK |
| `/recommendations` | Action cards | Q5 | No workflow status (New/Review/Planned/Done) |
| `/data` | Catalogue, quality, import | Data | No collector status / platform-support matrix |
| `/reports` | Exports | — | No print-friendly executive brief; CSV metadata lacks filters/model version |
| `/methodology` | Guide + experiments | — | Candidate table lives here (brief wants a Model Lab); no timed demo walkthrough |

## Missing screens required by the brief
- **Segment explorer (Q4, section D)** — comment/need-based segments (not people), with share, examples, campaign lift, trend, comparison.
- **Model lab (section H)** — pipeline stages, versioned config, experiment table, ADR-013 metric with definition, error cases, method comparison.
- **Executive brief** — printable, grounded in real numbers (section I).

## Cross-cutting gaps
Editorial typography + brief palette (current: Manrope, teal/violet on navy); Urdu Naskh font + `dir="rtl"` on Urdu-script excerpts; app-level `error.tsx`/`loading.tsx`; toasts for exports/status changes; sticky filter bar; breadcrumb depth on detail views; QA only at 375/1440 (brief wants 320/375/390/768/1280/1440); no axe-core checks; journey script covers 12 steps but not the brief's 10 named journeys.

## Constraints kept
No backend/model regressions; no new data fabricated; observed text stays withheld; no secrets read from other project folders (owner-consented YouTube key use already happened and is not needed for this work).
