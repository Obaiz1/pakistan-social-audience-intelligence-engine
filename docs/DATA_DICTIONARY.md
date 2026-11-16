# Data dictionary

Canonical DDL: `backend/audienceiq/storage/schema.sql`. Every bundle is loaded through it with `PRAGMA foreign_keys = ON`.
**Null means "not reported"** and is never replaced by zero.

## posts (assignment Table A + provenance)
| Field | Type | Notes |
|---|---|---|
| `dataset_id` | text, PK part | Dataset the row belongs to |
| `post_id` | text, PK part | `SYN-P#####` synthetic · `YT-<videoId>` observed · uploader's ID for imports |
| `source_id` | text, FK → sources | |
| `source_post_id` | text | Platform ID; `UNIQUE(platform, source_post_id, dataset_id)` |
| `brand` | text | Synthetic brands are fictional (`Brand A`–`Brand F`) |
| `platform` | enum | Instagram · TikTok · Facebook · YouTube · Other |
| `campaign_id`, `campaign` | text | Calendar campaign (synthetic), keyword-inferred (observed), or as uploaded |
| `content_type` | enum | reel · video · product_photo · influencer_post · styling_video · sale_announcement · other · unknown |
| `content_type_raw` | text | Original value before normalisation (never overwritten) |
| `product_category` | text | Single category per the assignment (women's lawn suits in the demo) |
| `likes`, `comments_count`, `shares`, `views` | integer ≥ 0, nullable | Shares null on YouTube; views null for photos/graphics |
| `published_at`, `snapshot_at` | ISO-8601 UTC | |
| `days_since_post` | integer ≥ 0 | Derived at snapshot |
| `source_url` | text, nullable | Null for synthetic rows (no URL is invented) |
| `source_type`, `dataset_origin`, `collection_method`, `reuse_permission`, `observed_vs_synthetic` | text | Provenance per row |
| `post_text` | text, nullable | Synthetic captions are marked `[synthetic caption]` |

Derived at request time (not stored): `interactions`, `er_views`, `er_formula`, `comment_ratio`, `mature`, `baseline_interactions`, `attention_index`, `er_index` — definitions in `analytics/engagement.py` and `/api/v1/methodology`.

## comments (assignment Table B)
| Field | Type | Notes |
|---|---|---|
| `comment_id` | text, PK part | Synthetic `SYN-C######`; imports/observed are salted hashes, never raw platform IDs |
| `post_id` | text, FK → posts | Join enforced |
| `comment_text` | text, nullable | Null when `text_permission = withheld` |
| `text_permission` | enum | full · illustrative (synthetic) · withheld |
| `language_type` | enum | english · roman_urdu · urdu · mixed · other (emoji-only) · unknown |
| `topic`, `topic_confidence` | text, 0–1 | **Reference** need label (rule lexicon) — used to name/audit clusters, not to form them |
| `sentiment` | enum | positive · neutral · negative · unknown (heuristic, supporting signal only) |
| `purchase_intent` | enum | strong_intent · possible_inquiry · none · unknown ("inquiry" ≠ purchase) |
| `published_at`, `like_count`, `char_len`, `source` | | Date-only timestamps for withheld datasets |

No usernames, author IDs, profile URLs, e-mails or phone numbers are stored; importer drops such columns and normalisation replaces in-text e-mails/phones/@mentions with placeholders before any model sees them.

## Model and decision tables
| Table | Key fields |
|---|---|
| `cluster_runs` | one row per candidate: representation, model, algorithm, params, seed, n_clusters, noise_rate, `metrics_json` (internal metrics, stability, external agreement), `selected` |
| `cluster_assignments` | selected run only: `comment_id → cluster_id`, cosine distance to centre, `is_noise` |
| `cluster_profiles` | label, need_category, label_agreement, size, share, cohesion, top terms, language/need mix, exemplars, date range, explanation |
| `anomaly_runs` / `anomaly_scores` / `anomaly_flags` | method & params; per-post cohort, robust z, comment-ratio z, Isolation Forest score; flags with value, baseline, P5–P95 range, score, direction, severity, reason, caveat |
| `recommendations` | action_type, title, what/why, audience need, where, linked evidence, priority, strength, sample size, metrics, limitations, test plan |
| `pipeline_runs` | build steps with timings |
| `datasets`, `sources`, `campaigns` | dataset metadata (mode, disclaimer, seed, expiry, text permission, manifest), source provenance, campaign calendar |

## Bundle files (`data/datasets/<dataset_id>/`)
One CSV per table above, `dataset.json` (dataset row + sources + SHA-256 manifest), `evaluation.json` (clustering candidates, audit, synthetic recovery, anomaly recovery, NLP summary). Synthetic bundles also contain `synthetic_truth_posts.csv` and `synthetic_truth_comments.csv` (generator ground truth, evaluation only — never read by the detectors or the API).
