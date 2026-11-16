# UI redesign: final handoff

**Status (2026-11-16):** the redesign is deployed to production and passes every automated check. It sits on branch `feat/ui-editorial-redesign` in **PR #3**, which is **not merged**: merging is the owner's decision.

| Item | Value |
|---|---|
| Live app | https://audienceiq-pk.vercel.app (`/api/v1/health` → `status: ok`, `build_commit: 80bf070…`, `problems: []`) |
| Pull request | https://github.com/Obaiz1/pakistan-social-audience-intelligence-engine/pull/3 |
| Commits | `b4a8a57` backend support · `9726dae` redesign · `80bf070` breadcrumb label + e2e waits (deployed) · then a docs/evidence-only commit |
| CI on PR #3 | backend ✓ · frontend ✓ · e2e ✓ (10 journeys **and** the axe-core screen sweep on Linux) |

## Production verification (run against https://audienceiq-pk.vercel.app after deploying 80bf070)
| Check | Result | Evidence |
|---|---|---|
| 10 user journeys + health | **11/11**, 0 console errors, 0 API errors | `docs/evidence/e2e-journey-redesign-prod.json` |
| Screen + axe sweep, synthetic | **68/68**, axe serious/critical 0 | `docs/evidence/qa-screens-redesign-prod.json`, `docs/screenshots/redesign-prod/` |
| Screen + axe sweep, observed YouTube | **68/68**, axe serious/critical 0 | `docs/evidence/qa-screens-redesign-prod-observed.json`, `docs/screenshots/redesign-prod-observed/` |

The first production journey run was 10/11: J8 (Data hub) and J7 (Model lab) checked their tables before the hosted API had answered, because the panel titles render during loading. The production API returned the same data as local (36 candidate runs, 4 platforms), so this was a test-timing problem; the tests now wait for the tables. It was not an app defect.

## What changed for users
- **Five-question story:** rail, stepper, overview answer cards and the printable brief follow attention → needs → unusual → segments → action.
- **New:** Segments (Q4), Model lab, Executive brief, Data hub source status.
- **Upgraded:** Action center with workflow status, an Audience evidence trail with Roman-Urdu gloss and linked posts, ranked anomaly flags with cohort warnings, filtered CSV with metadata, comment sort, and a demo walkthrough on the Methodology page.
- **Accessibility:** WCAG 2.1 AA checked by axe-core across 13 routes, 2 themes and 6 widths. Urdu renders right-to-left in Naskh, and the drawers trap focus.

## Honest limits
- The **`frontend-design` plugin was not installed and was not run.** It needs an interactive `/plugin install`. The brief's written design spec was followed instead.
- **Workflow status lives in this browser only** (`localStorage`). The hosted API is read-only, so status is not shared between people.
- **QA was Chromium only.** There was no manual screen-reader session and no Safari/Firefox run.
- **The observed YouTube snapshot expires 2026-12-16 07:58 UTC.** The Data hub shows the countdown. To refresh it, run `pipelines/collect_youtube.py` with the owner's key in the owner's own shell. The key never goes into the web app.

## Owner actions
1. Review and merge PR #3, if you want `main` to match production.
2. Optional: install the `frontend-design` plugin in an interactive session if you want a second design pass from it.
3. Refresh the YouTube snapshot before 2026-12-16.

## Where things are
Design system `docs/UI_DESIGN_SYSTEM.md` · route matrix `docs/UI_ROUTE_MATRIX.md` · QA details and fixes `docs/UI_QA_REPORT.md` · progress `docs/UI_PROGRESS.md` · audit `docs/UI_AUDIT.md`.
