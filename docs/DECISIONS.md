# Decisions (architecture decision records)

Each record: context → decision → consequences. Newest last.

## ADR-001 New standalone repository, sources cloned read-only
Context: two upstream projects exist (Repo A Content Detective, Repo B SignalSpend). Decision: create `pakistan-social-audience-intelligence-engine` as a fresh repository; upstream clones live in `../_upstream/` (outside this repo) for reading only; adapted code is copied with provenance headers; no nested `.git`. Consequence: upstream histories are untouched; this repo's history starts clean.

## ADR-002 Next.js + FastAPI in one Vercel project (Repo B layout)
Context: Vercel docs (checked 2026-11-15) list Python 3.12 (default), 3.13 and 3.14, a 500 MB uncompressed Python bundle limit, 300 s max duration and 4.5 MB request/response bodies on Hobby. Repo B deployed this exact layout successfully on 2026-11-02. Decision: Vercel root = `frontend/`; `frontend/api/index.py` imports the FastAPI app copied in at build time; `/api/v1/*` rewritten to it. Consequence: one URL, no CORS; the Python bundle must stay well under 500 MB, so torch/transformers are **not** deployed.

## ADR-003 Offline embedding + clustering, precomputed artifacts served online
Context: semantic sentence embeddings need torch (hundreds of MB) and minutes of CPU. Decision: `pipelines/` computes embeddings, compares clustering candidates and writes versioned tables (assignments, profiles, run metrics). The API only reads them. Runtime clustering for user-imported CSVs uses the lightweight TF-IDF word+char n-gram + SVD representation (scikit-learn only), clearly labelled as the lexical baseline. Consequence: no model download or training on any Vercel request.

## ADR-004 SQLite canonical store built from committed CSV tables
Context: the brief asks for canonical relational tables with keys/checks; Vercel's filesystem is not durable. Decision: canonical DDL in `backend/audienceiq/storage/schema.sql` (FKs, `UNIQUE(platform, source_post_id, dataset_id)`, CHECKs, indexes). Built-in datasets are committed as CSV tables (diff-able, Excel-openable) and loaded into an in-memory SQLite database at cold start with `PRAGMA foreign_keys = ON`, so integrity is re-verified on every start. Local user imports persist to `var/audienceiq_user.sqlite`. Consequence: hosted deployment is read-only; persistent hosted imports would need `DATABASE_URL` (not configured; see DEPLOYMENT.md).

## ADR-005 Synthetic classroom corpus is fictional and watermarked
Decision: seed-42 generator with fictional brands "Brand A–F" (real brand names are never attached to generated metrics), four platforms, lawn-suit category, multilingual compositional comment generator with spelling variants and code-switching, and a small set of injected anomalies whose ground truth is stored separately and used only for evaluation. Every response carries `SYNTHETIC DEMO — NOT REAL SOCIAL MEDIA OBSERVATIONS`.

## ADR-006 Observed data = YouTube Data API v3 only; comment text never redistributed
Context: Instagram/TikTok/Facebook public comment access needs app review or owner accounts not available here; YouTube Data API is authorised and Repo A already uses it. YouTube API policy requires stored API data to be refreshed or deleted within 30 days. Decision: observed collection reuses Repo A's client; raw text stays in git-ignored `data/observed/private/`; the shipped observed dataset holds post statistics and comment-level *derived* fields only (`comment_text = NULL`, `text_permission = withheld`), with `expires_at = snapshot + 30 days` enforced by the API. Consequence: the hosted observed view degrades to an "expired — refresh needed" state if not refreshed.

## ADR-007 Clustering model selection rule fixed before looking at results
Decision: candidates are compared on internal quality (cosine silhouette on a fixed sample), seed/bootstrap stability (ARI) and noise rate; the selection rule is "highest silhouette × stability among candidates with noise ≤ 35% and every cluster ≥ 1% of comments". Agreement with the synthetic generator's latent needs (ARI/NMI) and with the hand-labelled multilingual audit set is **reported, not used for selection**, so `k` is never tuned to reproduce rubric categories.

## ADR-008 Rule lexicon = interpretation aid, not the clustering
Decision: a multilingual keyword labeller produces a *reference* need label per comment. It is used (a) to name discovered clusters by majority vote with a reported agreement share, and (b) to audit them. Cluster membership comes only from the embedding + clustering pipeline.

## ADR-009 Anomalies are peer-cohort statistics, never fraud claims
Decision: robust (median/MAD) z-scores within the most specific peer cohort with ≥ 20 mature posts (brand × platform × content type → platform × content type → platform), threshold |z| ≥ 3.5 (Iglewicz–Hoaglin), plus Isolation Forest as a secondary multivariate score. Text always says "statistically unusual — investigate", never "fake" or "bot".

## ADR-010 Public demo is read-only
Decision: hosted deployment exposes all read endpoints and CSV *preview/validation*; it refuses dataset regeneration and persistent import writes (403 with an explanation) unless `AUDIENCEIQ_ALLOW_WRITES=1` and a durable store are configured. Upload bodies capped at 2 MB (below Vercel's 4.5 MB limit).

## Open items
- Licence for this repository: none chosen yet (owner decision). Upstream repos have no licence file.
