# UI route matrix

Every route, the question it answers, the API it reads, and how it is tested. All routes existed before the redesign except those marked **new**; none were removed or renamed.

| Route | Rail group | Question | Main API calls (`/api/v1/…`) | Key interactions | Journey | Screen QA |
|---|---|---|---|---|---|---|
| `/` | Start | Q1–Q5 overview | `analytics/overview` | Five answer cards → question pages; KPI links; needs bars → cluster; top actions | J1 | 390/1440 × light/dark + 320/375/768/1280 |
| `/content` | Five questions · 1 | Q1 Attention | `analytics/content`, `posts`, `posts/{id}` | Chart ⇄ table; post drawer; URL filters; **filtered CSV** with metadata header | J2 | 390/1440 × 2 themes |
| `/audience` | Five questions · 2 | Q2 Needs | `audience/clusters`, `audience/clusters/{id}` | Needs distribution → cluster detail; evidence trail (why → comments → posts → action); language filter; Roman-Urdu gloss; linked-post drawer | J3 | all six widths |
| `/anomalies` | Five questions · 3 | Q3 Unusual | `anomalies`, `anomalies/{flag}` | Ranked flags chart; drawer with cohort, baseline, broad/small-cohort warnings, caveat; focus trapped | J4 | 390/1440 × 2 themes |
| `/segments` **new** | Five questions · 4 | Q4 Segments | `audience/segments` | Segment cards (comments, share, agreement, examples, lift, trend, next action); compare by campaign/brand/content type/platform | J5, J10 | all six widths |
| `/recommendations` | Five questions · 5 | Q5 Action center | `recommendations` | Opportunity / Why / Evidence / Suggested test / Uncertainty; evidence chips; workflow status (browser-local) with toast; filters by type, priority, status | J6 | all six widths |
| `/comments` | Explore | Q2 detail | `comments`, `options` | Cluster/language/topic/intent/sentiment filters; **sort**; search; Urdu rendered RTL | J10 | 390/1440 × 2 themes |
| `/campaigns` | Explore | Q1/Q4 by campaign | `analytics/campaigns` | Campaign comparison; needs by campaign | — | 390/1440 × 2 themes |
| `/data` | Evidence & data | Data hub | `datasets`, `data/quality`, **`data/sources`**, `imports/preview` | Dataset catalogue; **source status + platform matrix (booleans only, never keys)**; quality audit; import wizard (preview-only when hosted) | J8 | 390/1440 × 2 themes |
| `/model` **new** | Evidence & data | How clusters were made | `methodology`, `audience/evaluation` | Pipeline stages; selected config; ADR-013 audit metric with definition (18 % → 52 %); candidate table; error cases; method comparison | J7 | 390/1440 × 2 themes |
| `/reports` | Evidence & data | Deliverables | `reports/export` | XLSX, PDF, CSV per section (filters applied); link to brief carrying current filters | J9 | 390/1440 × 2 themes |
| `/reports/brief` **new** | (from Reports) | Executive brief | `analytics/overview`, `recommendations` | Print / save as PDF; server PDF link; Q1–Q5 + limitations; print CSS hides navigation | J9 | 390/1440 × 2 themes |
| `/methodology` | Evidence & data | Method guide | `methodology`, `audience/evaluation` | Seven-minute demo walkthrough; formulas; gates; limitations; reproduce commands | — | 390/1440 × 2 themes |

## API additions made for the redesign (backend commit `b4a8a57`)
| Endpoint / field | Purpose |
|---|---|
| `GET /audience/segments` | Need-level comment segments with honest denominators, lift (n ≥ 15), monthly trend, examples (text `null` when withheld), linked recommendations, compare matrix (groups ≥ 30 comments) |
| `GET /data/sources` | Collector configured? (boolean), latest snapshot/expiry, platform support matrix. Never returns key values |
| `analytics/overview` → `needs`, `pipeline`, `dataset_created_at` | Needs distribution and pipeline status on the overview |
| `audience/clusters/{id}` → `gloss`, `gloss_note`, `linked_posts` | Roman-Urdu gloss shown as supporting info; top posts for the cluster |
| `comments?sort=` | `comment_id`, `published_at`, `char_len`, `cluster_id`, each with `-` for descending |
| `reports/export` CSV/XLSX metadata | Product, disclaimer, mode, dataset, snapshot, counts, clustering run, filters, rows, generated time, limitations |

Backend tests for these: `backend/tests/test_api.py` (109 passed after the additions).
