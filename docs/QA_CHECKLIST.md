# QA checklist

Each item names the automated check that covers it; results are recorded in `docs/TEST_EVIDENCE.md`.

## Data
- [ ] Synthetic corpus deterministic for a seed — `test_synthetic.py::test_deterministic`
- [ ] 2K–5K posts with associated comments; counts shown in UI and API — `/datasets`, banner, `test_api.py::test_datasets_contract`
- [ ] Post–comment join; unique IDs; no negative counts; no future dates — `test_storage.py`, `/data/quality` checks
- [ ] Null ≠ 0 for shares/views/likes — `test_engagement.py::test_missing_is_not_zero`, `test_storage.py::test_null_metrics_are_allowed_and_stay_null`
- [ ] Synthetic watermark on every route, API response and export — `test_api.py::test_every_route_returns_meta_envelope`, `test_exports`, `e2e/screens.mjs` (banner captured)
- [ ] Observed and synthetic never merged — separate bundles, `datasets.mode`
- [ ] Bundle integrity — CI step "Verify committed dataset bundles"

## Import
- [ ] Header mapping suggestions; strict numbers ("12%" rejected); negative/future/invalid dates reported with row numbers — `test_importer.py`
- [ ] PII columns dropped; orphans and empty comments skipped; Unicode kept — `test_importer.py::test_comments_pii_columns_dropped_orphans_and_empty_skipped_unicode_kept`
- [ ] Size limit (2 MB) and row limits — `api/app.py:_check_sizes`, `importer.MAX_*`
- [ ] Hosted mode read-only (confirm/demo/delete → 403), preview allowed — `test_api.py::test_hosted_mode_is_read_only_but_preview_works`
- [ ] Cross-site writes refused — `test_api.py::test_cross_site_write_refused`

## ML
- [ ] Non-trivial multilingual clusters on a hand-written fixture — `test_clustering.py::test_lexical_clustering_groups_multilingual_needs_nontrivially`
- [ ] Reproducible selection and assignments — `test_pipeline_selection_is_reproducible_and_reports_external_only`
- [ ] External agreement reported but not in the selection score — same test
- [ ] Mixed clusters labelled "Mixed" below 45 % agreement — `test_naming_reports_mixed_below_threshold`
- [ ] Anomalies: known outliers, no cross-platform mixing, tiny cohorts unscored, missing values, deterministic, no fraud language — `test_anomalies.py`
- [ ] Recommendations only from gated evidence — `test_recommendations.py`

## UI
- [ ] All 10 routes return 200 with an `h1`, no console errors, no API 5xx — `e2e/screens.mjs`
- [ ] No horizontal overflow at 375 px and 1440 px, dark and light — `e2e/screens.mjs`
- [ ] Every interactive control has an accessible name — `e2e/screens.mjs` (`unnamed` list)
- [ ] Chart ⇄ table toggle on charts; heat tables are real tables — `components/ui.tsx:ChartTable`, `charts.tsx:NeedHeat`
- [ ] Keyboard: skip link, focus rings, Escape closes drawers and mobile nav — `e2e/journey.mjs` (Escape on post drawer), manual
- [ ] Loading / empty / error / low-sample / no-permission states — `ui.tsx` (`LoadingPage`, `Empty`, `ErrorState`, `LowSample`, withheld `TextCell`)
- [ ] Five-question journey works end to end — `e2e/journey.mjs`

## Security
- [ ] No secrets in git — pre-commit grep for key patterns (see TEST_EVIDENCE), `.gitignore` covers `.env*`, `var/`, private observed data
- [ ] No usernames or raw platform comment IDs stored — importer + adapters hash IDs
- [ ] Exports guard against formula injection — `reports/export.py:safe_cell`
- [ ] Security headers — `next.config.ts`, API `X-Content-Type-Options`, `Cache-Control: no-store`

## Deployment
- [ ] Production URL opened; `/api/v1/health` = ok; every route 200; journey passes on production — `docs/DEPLOYMENT.md`
