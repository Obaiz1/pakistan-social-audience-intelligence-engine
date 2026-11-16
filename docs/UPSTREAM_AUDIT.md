# Upstream audit — what genuinely exists in the two source repositories

**Audit date:** 2026-11-15 · **Method:** read-only `git clone` into a sibling folder (`../_upstream/`, outside this repository), file-by-file reading, and re-running each project's own test suite in throwaway Python 3.12 virtual environments. Neither source repository was modified, pushed to, or re-configured.

## 1. Repositories inspected

| | Repo A — Pakistani Social Media Content Detective | Repo B — SignalSpend AI |
|---|---|---|
| URL | https://github.com/Obaiz1/pakistani-social-media-content-detective | https://github.com/Obaiz1/signalspend-ai |
| Default branch | `main` | `main` |
| Inspected commit | `957e3b6f2f978dcd60ab37a25f01cb05c88b8155` (2026-10-18, "Final report generator…") | `9c5f41520124f497aa7808d00aec7ee1d654398f` (2026-11-02, "Delete ATTRIBUTION.md") |
| Commits | 38 | 9 |
| Tracked files | 208 (incl. 100+ vendored `.claude/skills/*` files unrelated to the app) | 273 |
| License file | **None** | **None** |
| Owner | Obaiz1 (same owner as this Project 3) | Obaiz1 (same owner as this Project 3) |
| Stack (verified from files) | Python `>=3.12,<3.13`, pandas, pandera, scipy, statsmodels, scikit-learn, Streamlit, Plotly, fpdf2; optional `nlp` group: torch, transformers, sentence-transformers, BERTopic | Next.js 16.4.3, React 19.3.1, Tailwind 4.3.3, Recharts 3.10.1, lucide-react; FastAPI + pydantic 2 + pandas + scikit-learn + XGBoost backend; optional PySpark |

**Licensing note.** Neither repository has a LICENSE file, so neither is open source in the legal sense. Both belong to the same GitHub account that owns this Project 3 work, so reuse here is reuse **by the copyright owner**. Each adapted file in this repository carries a provenance header (`Adapted from Repo A …` / `Pattern from Repo B …`). If either source is ever re-licensed, this repository still needs its own license decision (recorded as an open item in `DECISIONS.md`).

## 2. Actual module map and what each part does

### Repo A (Python / Streamlit; YouTube Data API v3)

| Path | Verified contents |
|---|---|
| `src/ingestion/youtube.py` (134 lines) | `YouTubeClient`: API-key auth, full uploads-playlist paging (no early stop), 50-ID batching, quota meter, retry on 429/5xx, `QuotaExceededError`; `get_comments` returns top-level comments with author identity removed and the comment ID SHA-256-hashed. |
| `src/processing/normalize.py` | API items → canonical `channels` / `videos` / `comments` frames; missing metrics stay null (`Int64`). |
| `src/processing/features.py` | PKT conversion, ISO-8601 duration parsing, hashtag/emoji/script features, keyword campaign tags (`config/campaign_tags.yaml`, includes Urdu-script keywords). |
| `src/processing/metrics.py` | `er_views = (likes + comments) / views`, null-propagating ratios, `rel_er` (= ER / brand median ER over reliable videos), `likely_promoted` heuristic, `low_reliability` (< 100 views or < 14 days). |
| `src/analytics/compare.py` | `compare_groups`: per-group n, median, bootstrap 95% CI, Mann-Whitney U vs rest, Cliff's δ with effect labels, Benjamini-Hochberg, Kruskal-Wallis, `MIN_N = 20`. |
| `src/analytics/regression.py`, `timing.py`, `sentiment_agg.py` | Mixed-effects check, PKT time bands, brand/month sentiment aggregation. |
| `src/nlp/langid.py` | Script + lexicon language ID → `urdu_script` / `roman_urdu` / `english` / `mixed` / `other`. |
| `src/nlp/sentiment.py`, `benchmark.py` | VADER / Hugging Face / NVIDIA-LLM sentiment adapters; 250-comment benchmark (labels drafted by Claude, pending owner verification). |
| `src/nlp/topics.py` | **BERTopic on video *titles*** (`paraphrase-multilingual-MiniLM-L12-v2` + UMAP + HDBSCAN). **Comments are not clustered anywhere in Repo A.** |
| `src/recommendations/engine.py` | Evidence cards (what/where/when/why/n/limitations/A-B test) only from BH-significant findings with effect ≥ small; adjusted-model downgrade. |
| `src/recommendations/llm_wording.py` | Optional NVIDIA rewrite with a **number lock** (rejects any rewrite that introduces a number not in the card). |
| `src/validation/schemas.py` | Pandera schemas; refuses comment author columns (`FORBIDDEN_COMMENT_COLUMNS`). |
| `src/reporting/export.py` | Excel/CSV/PDF exports (fpdf2). |
| `app.py`, `views/*.py`, `src/ui.py`, `src/app_data.py` | Streamlit UI (8 pages); dataset priority: local snapshot < 30 days → live API → bannered synthetic fixture. |
| `data/synthetic_demo/` | 357 synthetic videos, 239 synthetic comments, 8 synthetic channels (`provenance = SYNTHETIC`). |
| `docs/DATA_AUDIT.md` | Real collection audit (2026-10-17): ~2,190 videos across 8 brands in 24 months, **~896 comments in total, only ~20% of videos have any comment**, 5 Urdu-script comments, signs of ad-inflated views, YouTube 30-day refresh/delete policy. |
| `.github/workflows/refresh-data.yml` | Weekly collection that publishes a snapshot **without comment text** to a private data repo. |

### Repo B (Next.js + FastAPI on Vercel)

| Path | Verified contents |
|---|---|
| `frontend/vercel.json`, `frontend/api/index.py`, `frontend/scripts/prepare-backend.mjs` | **Proven single-project Vercel layout**: Vercel root = `frontend/`; build copies the Python package into a git-ignored `.backend/`; `api/index.py` imports the FastAPI `app`; `/api/v1/:path*` is rewritten to the Python function. `docs/deployment.md` records a verified production deployment (2026-11-02). |
| `frontend/next.config.ts` | Local-dev rewrite of `/api/v1/*` to `127.0.0.1:8000`; security headers. |
| `frontend/components/shell.tsx`, `ui.tsx`, `charts.tsx`, `filters.tsx` | Responsive rail + topbar shell, mobile drawer with Escape, pre-paint theme script, `PageHead`/`Panel`/`Notice`/`Kpi`/`Empty`/`Skeleton`/`Segmented`/native `<dialog>`, platform colour + **marker shape** (WCAG 1.4.1). |
| `frontend/app/globals.css` (1,011 lines) | Dark/light token system, focus rings, reduced-motion, tabular numbers. |
| `frontend/lib/api.ts`, `format.ts` | Typed fetch adapter mirroring backend models; `errorText`; PKR formatting. |
| `backend/src/ads_optimizer/data/schema_mapping.py` | Deterministic header-alias suggestions, strict numeric parsing (no silent `12%` → 12), null tokens. |
| `backend/src/ads_optimizer/data/csv_importer.py` | Stage → validate → commit import flow with size limit. |
| `backend/src/ads_optimizer/analytics/metrics.py` | Ad KPIs (CTR, CPA, ROAS) and `safe_csv_cell` (CSV-injection guard). |
| `backend/src/ads_optimizer/hosting/workspace.py`, `api.py` middleware | Postgres-backed zipped workspace; public-demo mode that refuses deletes/key changes; origin check on writes. |
| `optimization/`, `ml/` (XGBoost), `benchmarks/` (Spark lab), `commerce/` | Budget allocation, revenue prediction, Big Data engine comparison, Shopify/commerce reconciliation. |

## 3. Existing tests (re-run during this audit)

See §8 for the exact commands and results recorded on 2026-11-15.

## 4. Reuse / Adapt / Reimplement / Exclude

| Source unit | Decision | Where it lives in Project 3 | Justification |
|---|---|---|---|
| A `ingestion/youtube.py` (`YouTubeClient`, `hash_id`) | **Reuse** (copied with provenance header) | `backend/audienceiq/data/youtube.py` | Tested, quota-aware, privacy-preserving official-API client. |
| A `processing/normalize.py` | **Adapt** | `backend/audienceiq/data/youtube.py` (`videos_to_posts`, `comments_to_rows`) | Must emit the Project 3 *post/comment* schema instead of *video* schema. |
| A `processing/metrics.py` (`_ratio`, `rel_er`, null rules) | **Adapt** | `backend/audienceiq/analytics/engagement.py` | Same "null is not zero" principle, generalised to platform-specific formulas and brand × platform baselines. |
| A `analytics/compare.py` | **Reuse** (copied) | `backend/audienceiq/analytics/stats.py` | Bootstrap CI, Mann-Whitney, Cliff's δ, BH are exactly what Q1 comparisons need. |
| A `nlp/langid.py` | **Adapt** | `backend/audienceiq/nlp/langid.py` | Kept the algorithm; output mapped to `english / roman_urdu / urdu / mixed / other / unknown`; small fashion-domain lexicon additions are recorded and evaluated on a held-out audit set. |
| A `processing/features.py` (`build_tag_matchers`, Urdu-substring logic) | **Adapt** | `backend/audienceiq/nlp/intent.py` | Same matcher technique reused for the multilingual *reference* need labeller (used to name and audit clusters, never as the clustering itself). |
| A `recommendations/engine.py` (card fields, A/B text, significance gate) | **Adapt** | `backend/audienceiq/recommendations/` | Card anatomy kept; evidence now links cluster IDs, anomaly flags and campaign comparisons. |
| A `recommendations/llm_wording.py` (number lock) | **Adapt** | `backend/audienceiq/recommendations/wording.py` | Optional, off by default, never on the public deployment. |
| A `nlp/topics.py` (BERTopic on titles) | **Exclude as audience clustering**; embedding model choice reused | — | Clustering video titles does not answer Q2/Q4. Project 3 clusters **comments**. |
| A `validation/schemas.py` (forbidden author columns) | **Adapt** | `backend/audienceiq/data/validation.py` | Same PII guard, applied to the import pipeline. |
| A `reporting/export.py` | **Reimplement** (smaller) | `backend/audienceiq/reports/export.py` | Different tables; same CSV/Excel/PDF idea with fpdf2. |
| A Streamlit `app.py`, `views/` | **Exclude** | — | Streamlit's websocket server cannot run as a Vercel function; UI rebuilt in Next.js. |
| A sentiment benchmark, thumbnails/VLM, engagement ML | **Exclude** | — | Not needed for Q1–Q5; sentiment is only an optional supporting signal here. |
| B Vercel layout (`vercel.json`, `api/index.py`, `prepare-backend.mjs`, `next.config.ts` rewrites) | **Reuse** (adapted names) | `frontend/` | Verified working on Vercel on 2026-11-02 with the same Next/React versions. |
| B `shell.tsx`, `ui.tsx`, theme script, `globals.css` tokens | **Adapt** | `frontend/components/`, `frontend/app/globals.css` | Accessible, responsive, dark/light; re-branded to AudienceIQ PK and new navigation. |
| B `charts.tsx` | **Reimplement** | `frontend/components/charts.tsx` | Different chart types (cluster bars, bubbles, distributions); keeps the "chart + data table" parity idea. |
| B `schema_mapping.py` (`normalized_name`, `numeric_values`, `NULLS`) | **Adapt** | `backend/audienceiq/data/importer.py` | Header suggestion + strict number parsing for post/comment CSVs. |
| B `safe_csv_cell` | **Reuse** | `backend/audienceiq/reports/export.py` | CSV/Excel formula-injection guard. |
| B public-demo write guard + origin check | **Adapt** | `backend/audienceiq/api/app.py` | Public demo must not let anonymous users overwrite shared data. |
| B budget optimizer, XGBoost revenue ML, Spark lab, commerce, NVIDIA assistant, Postgres zipped workspace | **Exclude** | — | Out of scope for Q1–Q5; ROAS/ad-spend metrics must not be confused with organic post engagement. |

## 5. Schema conflicts and how they are resolved

| Conflict | Repo A | Repo B | Project 3 resolution |
|---|---|---|---|
| Unit of analysis | YouTube **video** (`video_id`) | Ad **campaign-day** row | Canonical **post** (`post_id`, `platform`, `source_post_id`); a YouTube video becomes a post with `platform = YouTube`, `content_type = video` (no reel/short claim without evidence). |
| Campaign | Keyword tags inferred from titles (multi-label) | Advertiser campaign name | `campaign` is a post attribute; for observed YouTube it is **inferred from title keywords** and labelled `campaign_source = keyword_inferred`. |
| ID namespaces | `video_id`, hashed `comment_id_hash` | `dataset_id` + row index | Unique `(platform, source_post_id, dataset_id)`; comments keyed `(dataset_id, comment_id)`; synthetic IDs prefixed `SYN-`. |
| Counts vs rates | Counts from API, ER computed | Spend/CTR/ROAS rates | Store raw counts only (nullable); every rate computed in code with its denominator recorded. No spend/ROAS. |
| Shares / views | Shares never available; views always | n/a | `shares` and `views` nullable per platform; missing ≠ 0 everywhere. |
| Observed vs synthetic | Separate fixture folder + banner | `is_synthetic` flag on manifests | `datasets.mode ∈ {synthetic, observed, imported}`; every API response carries `meta.mode` and `meta.disclaimer`; datasets never merged. |
| Comment text | Never published | n/a | Synthetic text shown (labelled illustrative). Observed YouTube text stays local; hosted observed rows carry `comment_text = NULL`, `text_permission = withheld`. |

## 6. Integration architecture

Next.js App Router frontend (patterns from Repo B) + FastAPI backend in the **same Vercel project**, using Repo B's proven layout. The backend is a new package `audienceiq` holding adapted Repo A logic plus new Project 3 modules (comment clustering, anomaly detection, need-linked recommendations). Heavy work (sentence embeddings, model selection) runs **offline** in `pipelines/`; the deployed function serves precomputed, versioned artifacts from committed CSV tables loaded into SQLite at cold start. Details: `docs/ARCHITECTURE.md`, `docs/DECISIONS.md`.

## 7. Current state vs the five assignment questions (before Project 3 work)

| Question | Repo A | Repo B | Gap to close in Project 3 |
|---|---|---|---|
| Q1 Which content attracts attention? | Partial: YouTube-only, duration buckets and keyword campaign tags; no reels/photos/influencer/styling types | Ad campaign KPIs (spend-based), not organic engagement | Multi-platform post model, content-type and campaign comparison with platform-specific formulas. |
| Q2 What does the audience want? | Language ID and sentiment only; **no need/topic grouping of comments** | None | **Comment embeddings + unsupervised clustering**, multilingual. |
| Q3 Which patterns are unusual? | `likely_promoted` heuristic only | None | Peer-cohort robust z + Isolation Forest post anomaly detection with reasons. |
| Q4 Which needs to address? | None | None | Cluster profiles: counts, shares, language mix, campaign lift, exemplars, caveats. |
| Q5 What to do next? | Evidence cards from content/timing findings | Budget allocation (out of scope) | Recommendations that link cluster, anomaly and campaign evidence, with test plans. |

## 8. Upstream test reproduction (executed 2026-11-15, Windows 11, Python 3.12.15)

| Repo | Command (inside a fresh venv) | Result |
|---|---|---|
| A | `pip install -r requirements.txt pytest` then `python -m pytest -q -p no:cacheprovider` | **122 passed** in 71.7 s, exit 0 (README claims 110; the suite has grown) |
| B | `pip install -e ".[dev]"` then `python -m pytest -q -p no:cacheprovider` | **200 passed, 8 failed, 3 skipped** in 221 s, exit 1 |

Repo B's 8 failures are all environment-specific to Windows, not logic defects in code reused here: 4× `PermissionError [WinError 32]` (SQLite temp file still open when `TemporaryDirectory` is removed), 2× POSIX file-mode assertions (`0o600` expected, Windows reports `0o666`), 1× `WinError 1314` (creating a symlink needs a privilege), 1× `os.killpg` missing on Windows (`test_cleanup_kills_orphan_group_after_runner_exits`). None of the failing modules (`hosting/workspace.py`, `ai/nvidia.py` key file, `benchmarks/`, `commerce/`) is reused by Project 3.

## 9. Access problems

None: both repositories cloned anonymously over HTTPS. The original assignment `Project 3 (1).docx` was readable at `C:\Users\obaiz\Downloads\` and was transcribed into `docs/assignment/PROJECT3_REQUIREMENTS.md`. The docx itself is not committed (it is the instructor's document).
