# Traceability matrix

Requirement IDs come from `docs/assignment/PROJECT3_REQUIREMENTS.md` (transcribed from the instructor's document).
Status legend: **DONE+VERIFIED** (implemented and checked by a listed test/run) · **DONE** (implemented, manual check only) · **BLOCKED** (needs owner action).

| ID | Requirement | Code | API | UI | Tests / evidence | Status |
|---|---|---|---|---|---|---|
| R-TASK-1 | Group similar audience behaviours | `clustering/pipeline.py`, `candidates.py`, `profile.py`, `nlp/embeddings.py` | `GET /audience/clusters`, `/audience/clusters/{id}` | `/audience` | `test_clustering.py` (multilingual fixture, reproducibility, selection), `evaluation.json`, `docs/CLUSTERING_EVALUATION.md` | DONE+VERIFIED |
| R-TASK-2 | Identify unusual patterns | `anomalies/detect.py` | `GET /anomalies`, `/anomalies/{flag_id}` | `/anomalies` | `test_anomalies.py`, `evaluation.json → anomaly_recovery`, `docs/ANOMALY_METHOD.md` | DONE+VERIFIED |
| R-TASK-3 | Convert discoveries into decisions | `recommendations/engine.py` | `GET /recommendations` | `/recommendations`, overview cards | `test_recommendations.py`, `test_api.py::test_anomalies_and_recommendations_contracts` | DONE+VERIFIED |
| R-TASK-4 | Not merely positive/negative classification | Sentiment is an optional column only; Q2/Q4 come from clustering | `/comments` (sentiment labelled heuristic) | `/comments`, `/audience` | `test_nlp.py::test_sentiment_heuristic`; no endpoint ranks by sentiment | DONE+VERIFIED |
| R-APP | Small web application answering five questions | `frontend/` (10 routes) + FastAPI | `/api/v1/*` | all routes; "Try this project" journey on `/` | `frontend/e2e/journey.mjs` → `docs/evidence/e2e-journey-*.json`; `e2e/screens.mjs` | DONE+VERIFIED (see TEST_EVIDENCE) |
| R-Q1 | Compare reels, product photos, influencer posts, styling videos, sale announcements, Eid campaigns using likes/comments/shares/views where available | `analytics/engagement.py`, `analytics/content.py`, `analytics/stats.py` (Repo A) | `/analytics/content`, `/analytics/campaigns`, `/posts` | `/content`, `/campaigns` | `test_engagement.py` (hand-calculated ER, null≠0, share-coverage rule, weighted ER), `test_api.py` | DONE+VERIFIED |
| R-Q2 | Group comments around price, fabric quality, sizing, delivery, discounts, availability, purchase interest | embeddings + clustering; post-hoc naming via `nlp/intent.py` | `/audience/clusters`, `/comments` | `/audience`, `/comments` | `test_clustering.py`, `test_nlp.py` (assignment examples), audit set (100 comments) | DONE+VERIFIED |
| R-Q3 | Posts whose engagement/comment patterns differ from comparable posts | peer cohorts, robust z, comment ratio, need-mix, Isolation Forest | `/anomalies` | `/anomalies` (drawer: baseline, range, reason, caveat) | `test_anomalies.py`; injected-anomaly recall | DONE+VERIFIED |
| R-Q4 | Discover discount-focused, delivery-concerned, availability-asking groups | `clustering/profile.py`; needs-by-campaign/platform lift | `/audience/clusters` (needs_by_campaign), `/analytics/campaigns` | `/audience` heat tables, `/campaigns` | `test_api.py::test_clusters_and_detail`, `test_filtered_cluster_counts_shrink` | DONE+VERIFIED |
| R-Q5 | Evidence-based recommendations for content, promotions, customer service, campaign testing | gated cards with linked evidence, test plans | `/recommendations`, `/recommendations/{id}` | `/recommendations` | `test_recommendations.py` (gates, no unsupported cards) | DONE+VERIFIED |
| R-DATA-1 | Single product category (women's lawn suits) | `data/synthetic.py` (`CATEGORY`) | `meta.product_category` | hero, method notes | `test_synthetic.py::test_single_category_and_fictional_brands` | DONE+VERIFIED |
| R-DATA-2 | ~2,000–5,000 post records + comments | seed-42 generator: 3,000 posts | `/datasets` counts | banner, `/data` | `docs/DATA_PROVENANCE.md` (exact counts), `test_api.py::test_datasets_contract` | DONE+VERIFIED (synthetic) |
| R-DATA-3 | Permitted access only; don't assume comments/analytics downloadable | YouTube official API client only; CSV import with attestation; no scraping code | `/imports/*` | `/data` | `docs/DATA_PROVENANCE.md`; ADR-006/012 | DONE (observed collection BLOCKED: owner key) |
| R-DATA-A | Table A fields | `storage/schema.sql` posts | `/posts` | `/content` explorer | `test_storage.py`, `docs/DATA_DICTIONARY.md` | DONE+VERIFIED |
| R-DATA-B | Table B fields | schema comments + `services/build.py:enrich_comments` | `/comments` | `/comments` | `test_storage.py`, `test_nlp.py` | DONE+VERIFIED |
| R-DATA-4 | Examples are illustrative, not measurements | fictional brands; synthetic watermark everywhere | `meta.disclaimer` on every response | banner on every route, exports | `test_api.py::test_every_route_returns_meta_envelope`, export test | DONE+VERIFIED |
| R-DATA-5 | Keep source URL, collection date, provenance, reuse permissions | `sources` table, per-row provenance columns, manifest | `/datasets`, `/data/quality` | `/data` | `docs/DATA_PROVENANCE.md` | DONE+VERIFIED |
| R-DATA-6 | Separate actual observations from generated records | `datasets.mode`; never merged; separate bundles | `meta.mode` | mode badge + switcher | `test_api.py::test_datasets_contract`, import test (mode = imported) | DONE+VERIFIED |
| R-SRC-1 | Check the 2026 paper's dataset/code availability | — | — | `/methodology` limitations | `docs/assignment/PROJECT3_REQUIREMENTS.md` findings | DONE (not available → not used) |
| R-SRC-2 | E-commerce data is transactions, not comments | — | — | — | same | DONE (not used) |
| R-SRC-3 | Fashion catalogue = context only | — | — | — | same (licence unclear, menswear) | DONE (not used) |

## Brief-level (master prompt) requirements
| Requirement | Where | Status |
|---|---|---|
| Upstream audit with reuse table | `docs/UPSTREAM_AUDIT.md` | DONE+VERIFIED (tests re-run) |
| Clustering central; baseline vs candidates; manual multilingual audit | `docs/CLUSTERING_EVALUATION.md`, `/methodology` candidate table | DONE+VERIFIED |
| Model/run metadata with every result | `meta` envelope (`run_id`, `model_version`, `sample_size`, `generated_at`, `assumptions`) | DONE+VERIFIED |
| Dark/light, mobile 375–1440, chart⇄table, keyboard | `globals.css`, `ChartTable`, `Drawer`, skip link | see `docs/evidence/qa-screens-*.json` |
| Read-only public demo, upload limits, origin check | `api/app.py:guard` | `test_api.py::test_hosted_mode_is_read_only_but_preview_works`, `test_cross_site_write_refused` |
| Exports CSV/Excel/PDF with disclosures | `reports/export.py` | `test_api.py::test_exports` |
| Vercel deployment verified | `docs/DEPLOYMENT.md` | see DEPLOYMENT status |
| Observed YouTube data | `pipelines/collect_youtube.py` | BLOCKED: NEEDS OWNER ACTION (ADR-012) |
