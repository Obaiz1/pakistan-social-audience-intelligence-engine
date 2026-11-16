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

## ADR-007a Amendment (2026-11-16): selection runs within the semantic family; lexical is the baseline
Context: the brief names a multilingual sentence-embedding model as the method and TF-IDF/char-n-gram + SVD as "an explainable baseline, not a fake semantic model". Exploratory runs (docs/evidence/clustering_exploration_*.log) showed that character n-gram silhouettes are inflated by near-duplicate templated text, and that e5-small clusters strongly by language (NMI with language ≈ 0.31) whereas multilingual MiniLM and mpnet stay near 0.13–0.15. Decision: the ADR-007 rule is applied unchanged, but only `semantic` and `hybrid` candidates may be selected; `lexical` candidates are computed and reported as the baseline. The semantic model is `paraphrase-multilingual-mpnet-base-v2` (Apache-2.0), chosen on language invariance and internal silhouette at eligible k. Disclosure: the exploratory logs also printed agreement with the synthetic generator's hidden needs; those numbers were visible when choosing the model family and are reported, never used inside the selection rule.

## ADR-011 Boilerplate removal before embedding
Greetings, politeness markers and PII placeholders ("AOA sis … please", `<user>`) carry no audience need but dominated short-comment embeddings (unique texts fell from 12,230 to 7,859 after removal). Only that closed list is removed (`nlp/normalize.py:BOILERPLATE`); question words, products, sizes and places are never removed.

## ADR-012 Observed collection status (updated 2026-11-16: collected after explicit owner authorisation)
The collector (`pipelines/collect_youtube.py`) is implemented. Running it with a key found in another local project's `.env` was refused by the session's permission policy, so no observed data was collected in this build. The owner can run it with their own key in the environment (`YOUTUBE_API_KEY=… python pipelines/collect_youtube.py`); the resulting bundle ships with comment text withheld and a 30-day expiry.

## ADR-013 Roman-Urdu gloss in the embedding input (2026-11-16)
Context: the first full build selected semantic KMeans k = 8 under the ADR-007 rule; half of its clusters were "Mixed" and the independent audit placed Roman Urdu comments correctly only 2.7 % of the time — the multilingual encoder does not understand Roman Urdu well, so Roman-Urdu function words ("kitne", "milega", "hai") held clusters together. The brief explicitly requires handling transliteration and code-switching. Decision: for comments detected as Roman Urdu or mixed, the *embedding input only* is passed through a word/phrase **translation** gloss (`nlp/gloss.py`, e.g. "kitne din" → "how many days"; glosses never insert need labels — unit-tested). Stored text, exemplars and top terms keep the original wording. Evidence (`docs/evidence/clustering_exploration_4_gloss.log`): the gloss raises the *internal* selection score (best silhouette × stability 0.169 → 0.192), so the unchanged ADR-007 rule prefers it on internal grounds; reported agreement also rose (synthetic need NMI 0.24 → 0.45; audit 0.18 → 0.46). Disclosure: the gloss list was written after seeing the k = 8 failure; it covers common Roman Urdu words (general knowledge, like Project 1's lexicon), but overlaps with the generator's vocabulary, so the audit set is the fairer measure.

## ADR-014 Hierarchical refinement considered and not adopted
Splitting each rule-selected cluster when internal sub-structure exists (silhouette ≥ 0.06, stability ≥ 0.6, children ≥ 1 %) produced 25 stable leaves with the same need agreement as flat KMeans at k ≈ 24 (`docs/evidence/clustering_exploration_3_hierarchical.log`). It added complexity without fixing the representation problem, so it was not adopted.

**Update (2026-11-16):** after the owner explicitly asked for it, the collector ran once with the key from the owner's Project 1 folder: 2,165 videos from 8 official channels (24 months) and 809 top-level comments, 663 quota units. Bundle `observed-youtube-20261116` ships with comment text withheld, salted IDs and `expires_at = 2026-12-16`. Follow-ups: (1) the first run stored no comment dates because the adapter read `published_at` while Repo A's client returns `published_at_utc` (fixed + regression test); (2) a second collection to repopulate dates was refused by the permission policy, so comment dates stay empty in this snapshot until the owner re-runs the collector.
