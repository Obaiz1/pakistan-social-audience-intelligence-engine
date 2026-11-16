# Unusual-post detection (Q3) — method

Implementation: `backend/audienceiq/anomalies/detect.py` · tests: `backend/tests/test_anomalies.py`.

## Principle
A post is unusual only **relative to comparable posts**. Platforms, brands, formats and post ages are not exchangeable, so every score is computed inside a peer cohort, and every flag is described as a statistical outlier "for further investigation" (assignment wording) — never as fraud, bots or paid activity.

## Steps
1. **Scored population.** Mature posts (≥ 7 days old at snapshot) with a non-null primary metric. Immature posts and posts with unknown interactions (e.g. hidden likes) are not scored; their counts are reported.
2. **Primary metric.** `er_views = interactions / views` where views are reported; otherwise `interactions`. The metric kind is part of the cohort key, so view-based and count-based posts are never compared with each other.
3. **Peer cohort (hierarchical fallback).** The most specific of brand × platform × content type → platform × content type → platform with at least **20** scored posts. Posts with no qualifying cohort are left unscored instead of being compared with dissimilar posts.
4. **Engagement outlier.** Robust z = (log value − cohort median of log values) / (1.4826 × MAD). The log makes multiplicative differences symmetric; median/MAD resist the very outliers being searched for. |z| ≥ **3.5** flags (Iglewicz & Hoaglin's modified z-score threshold); |z| ≥ 5 = high severity. Positive = far above peers, negative = far below.
5. **Comment pattern.** Same robust z on log(comments ÷ likes), only for posts with ≥ 20 comments (small counts are noisy). Catches complaint storms, question floods and giveaways.
6. **Need-mix shift.** For posts with ≥ 8 clustered comments, the most over-represented *discovered* need is tested against its pooled share among cohort posts with an exact one-sided binomial test, Bonferroni-corrected within the post and Benjamini–Hochberg across posts; flagged when adjusted p < 0.01, the share is ≥ 40 % and ≥ 2× expected. This links Q3 to the clustering of Q2.
7. **Multivariate check.** Isolation Forest (200 trees, `random_state=42`, contamination "auto") on [engagement z, comment-ratio z, need-mix excess]. It is a secondary score attached to every post; posts that only Isolation Forest isolates (top 1 %) are listed as lower-confidence "multivariate" flags.

## What each flag shows
Post, kind, metric, value, cohort median, typical range (cohort P5–P95), score, Isolation Forest score, direction, severity, cohort key/level/size, an exact reason sentence with the numbers, the caveat, and the original source link when one exists. The UI adds the cohort distribution with the post's bin highlighted and the post's comment-need mix vs its cohort.

## Validation
- **Unit fixtures** (`test_anomalies.py`): known high and low outliers are found and ordinary posts are not; platforms are never mixed; tiny cohorts and immature posts are not scored; missing values and zero views do not crash; a seeded complaint-heavy comment mix is detected; outputs are deterministic; reason/caveat text never alleges fraud.
- **Synthetic recovery** (`evaluation.json → anomaly_recovery`): recall against anomalies deliberately injected into the synthetic corpus (viral spikes, engagement collapses, comment surges, giveaway floods). Precision is a lower bound because natural extremes in the simulation are also legitimately unusual. Figures are reported in `docs/CLUSTERING_EVALUATION.md` §Anomalies and on `/methodology`.
- **Sensitivity**: counts of engagement flags at |z| ≥ 3.0 / 3.5 / 4.0 / 5.0 are stored in `anomaly_runs.metrics_json`.

## Known false-positive sources
Boosted/paid reach (high views, normal likes → negative engagement outliers), influencer reposts, giveaways, data-entry errors in imports, and campaigns that genuinely perform differently. Each is listed as a possible explanation, and the recommended action for anomaly clusters is "investigate before repeating or dropping the approach".
