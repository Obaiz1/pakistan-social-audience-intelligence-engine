# Project 3 — Final Report

**Pakistan Social Audience & Campaign Intelligence Engine (Clustering Based)**
Application: *Pakistan Audience & Campaign Intelligence (AudienceIQ PK)* · Report date: 16 November 2026

> All quantitative results in this report come from a **synthetic classroom dataset** (seed 42, fictional brands). They demonstrate that the methods work end to end; they are not findings about real Pakistani brands or audiences.

## 1. Problem
A Lahore-style online clothing brand running Instagram, TikTok and Facebook campaigns (11.11, 12.12, Eid) receives thousands of comments in English, Roman Urdu and Urdu — "Price please?", "Delivery kitne din mein hogi?", "Ordered last week, still waiting." — but cannot see which customer needs and content patterns are hidden inside them. The assignment asks for an engine that **groups similar audience behaviour, identifies unusual patterns and converts the discoveries into marketing decisions**, explicitly going beyond positive/negative sentiment.

## 2. Objectives (the five questions)
Q1 which content attracts attention · Q2 what the audience wants · Q3 which marketing patterns are unusual · Q4 which audience needs the brand should address · Q5 what the marketing team should do next — all answerable in a small web application.

## 3. Data
- **What was available.** The assignment's suggested sources were checked: the 2026 journal article states no data/code availability; the Pakistan e-commerce dataset contains transactions, not comments; the fashion catalogue has an unclear licence and a different category. Public Instagram/TikTok/Facebook comments are not legitimately downloadable without platform approval. YouTube's official API is usable: an observed snapshot was collected on 16 November 2026 (2,165 videos from 8 official channels over 24 months, 809 top-level comments, 663 quota units). It is a separate dataset with comment text withheld and a 30-day expiry (`docs/DATA_PROVENANCE_OBSERVED.md`).
- **What was built.** A deterministic synthetic corpus (3,000 posts, 33,776 comments, single category: women's lawn suits) that simulates brand-owned analytics exports across four platforms, with platform-honest missing metrics, a campaign calendar (Eid, 11.11, 12.12, launches, festive), multilingual compositional comments and ~3 % injected anomalies with separate ground truth. Every page, API response and export carries *SYNTHETIC DEMO — NOT REAL SOCIAL MEDIA OBSERVATIONS*. Details: `docs/DATA_PROVENANCE.md`, `docs/DATA_DICTIONARY.md`.
- **Real-data paths.** CSV import with field mapping, validation and a source attestation (persisted locally), and a YouTube collector that withholds comment text and expires data after 30 days.

## 4. Methods
Summarised here; full detail in `docs/METHODOLOGY.md`.
- **Q1:** platform-specific engagement formulas, an *attention index* relative to each brand × platform baseline, maturity filter (≥ 7 days), medians with bootstrap CIs, Mann-Whitney + Cliff's δ + Benjamini–Hochberg (statistics reused from Project 1).
- **Q2/Q4:** normalisation (Urdu letter forms, Roman-Urdu spellings, PII placeholders, emoji tokens) → greeting/politeness removal → Roman-Urdu translation gloss (embedding input only) → multilingual sentence embeddings (`paraphrase-multilingual-mpnet-base-v2`) with TF-IDF/character-n-gram and hybrid alternatives → KMeans and UMAP+HDBSCAN candidates → selection by a fixed internal rule (silhouette × stability with noise and size gates) → post-hoc naming by a multilingual keyword reference labeller with the agreement share shown → profiles (size, share, language mix, campaign/platform lift, exemplars, cohesion, explanation).
- **Q3:** peer-cohort robust z-scores (median/MAD) of log engagement and log comments-per-like, a binomial test of each post's discovered-need mix against its cohort, Isolation Forest as a secondary multivariate score; reasons and a non-accusatory caveat on every flag (`docs/ANOMALY_METHOD.md`).
- **Q5:** deterministic recommendation cards emitted only when evidence passes explicit gates, each with linked evidence, sample size, limitations and an A/B or customer-service test.

## 5. Results (synthetic demo, seed 42)
Generated tables: `docs/CLUSTERING_EVALUATION.md` (all 36 clustering candidates, clusters, audit, recovery, anomalies) and `docs/DATA_PROVENANCE.md`.

**Q1 — content.** 2,895 mature posts compared (93 younger than 7 days excluded). Median attention index: influencer posts 1.51 (95 % CI 1.42–1.62, Cliff's δ medium), reels 1.27 (1.15–1.40), styling videos 1.22 (1.09–1.31), videos 0.90, sale announcements 0.80 (0.74–0.87), product photos 0.64 (0.59–0.69, medium); Kruskal–Wallis p < 0.001, every group BH-significant vs the rest. Eid ul Fitr (1.55) and Eid ul Adha (1.37) are the only campaigns significantly above the rest (small effects); 11.11 has only 14 mature posts and is not tested. Weighted engagement rate by platform: TikTok 9.4 %, Instagram 6.6 %, Facebook 4.0 %, YouTube 1.9 % — not directly comparable because formulas differ.

**Q2/Q4 — audience needs.** 36 candidates were evaluated (lexical / semantic / hybrid × KMeans k = 8…28 and UMAP+HDBSCAN). Every HDBSCAN candidate failed the gates (≥ 29 % noise or hundreds of tiny groups). The rule selected **semantic KMeans k = 8** (silhouette 0.223, stability 0.764, smallest cluster 4.6 %). Clusters: Price / cost 17.4 % (name agreement 72 %), Other / unclear 17.1 % (49 %), Compliments 15.9 % (50 %) and 13.9 % (73 %), Delivery & shipping 12.9 % (47 %), Availability & stock 11.3 % (61 %), Size & fit 7.0 % (81 %), Fabric & quality 4.6 % (80 %). NMI with language is 0.02, so groups are not language-driven. Agreement with the generator's hidden needs: ARI 0.356, NMI 0.429, purity 59 %. Independent audit: 52 % (English 65 %, Urdu 50 %, Roman Urdu 35 %); the rule labeller scores 81 % on the same set — clustering discovers structure without labels but is less precise than a hand-written lexicon on the needs that lexicon was written for. Discount questions merge into the Price cluster.

The path to this model is part of the result: the first full build (no Roman-Urdu gloss) also selected k = 8 but produced four "Mixed" clusters and 18 % audit accuracy (2.7 % on Roman Urdu). Adding a translation gloss for Roman-Urdu embedding inputs raised the internal selection score and the audit to 52 % (ADR-013; logs in `docs/evidence/`).

**Q3 — unusual posts.** 2,895 posts scored (cohorts: 2,403 at brand × platform × type, 492 at platform × type). 70 flags on 66 posts: 36 engagement (48 above / 22 below peers overall), 19 comment-pattern, 6 need-mix, 9 multivariate. Recall of the 94 injected anomalies: 53 % (engagement collapses 18/24, giveaway floods 12/14, viral spikes 12/36, comment surges 8/20); 76 % of flagged posts were injected ones. Example reason: *"Engagement rate 1.21 % vs cohort median 7.38 % (P5–P95 4.85 %–10.31 %) among 30 mature Brand D Instagram styling-video posts; robust z = −11.5."*

**Q5 — recommendations.** 18 cards passed the gates: 5 need cards (price, availability, size guide, fabric, compliments), 5 concentration cards (e.g. Brand E size & fit 13.9 % vs 7.6 %, 1.8×; sale announcements → availability 21.5 % vs 12.6 %; styling videos → fabric 7.7 % vs 5.1 %; Brand F availability 1.5×), 5 content cards (more influencer posts, reels, styling videos; rethink product photos and sale announcements) and 4 investigation/service cards from recurring anomalies. Brand C's simulated delivery problems do not produce a card because the Delivery cluster's name agreement (47 %) is below the 50 % gate — a limitation of the clusters, reported rather than tuned away.

### 5b. Observed YouTube snapshot (real data)
Generated tables: `docs/CLUSTERING_EVALUATION_OBSERVED.md`. 2,165 public videos (Sapphire 590, Nishat Linen 576, Gul Ahmed 330, Khaadi 199, Limelight 134, Bonanza Satrangi 116, Alkaram 113, J. 107); only 809 comments exist across them, mostly English (472) and Roman Urdu (164), with 150 emoji-only. Clustering selected semantic KMeans k = 4 (silhouette 0.303, stability 0.978): Compliments 38.9 % (81 % name agreement), Price / cost 7.8 % (79 %), and two "Other" groups (music/general questions; Roman-Urdu chatter). Real YouTube comments are dominated by praise and off-topic remarks, so the commerce needs that dominate the synthetic corpus (delivery, sizing, availability) barely appear: a platform difference worth stating, not a model failure. Q3 is the strongest observed finding: 168 of 171 flags are videos whose engagement rate is far below their own brand's peers (e.g. 0.01 % vs a 1.48 % median), the signature of paid/boosted views that Project 1 also reported. Three recommendations pass the gates (check high-reach low-engagement videos; answer price questions; reuse praised content). Limitations: YouTube only, viewer location unknown, campaigns inferred from title keywords, comment dates missing in this snapshot (adapter bug fixed after collection).

## 6. Application
Ten routes (overview with a guided Q1–Q5 path, content, audience, comments, anomalies, campaigns, recommendations, data, reports, methodology) built with Next.js 16 / React 19 / Tailwind 4 / Recharts on a FastAPI backend, deployed as one Vercel project (layout reused from SignalSpend). Charts have table equivalents; filters live in the URL; dark/light themes; mobile layout from 375 px; loading, empty, error, low-sample and withheld-text states. Screenshots: `docs/screenshots/`.

## 7. Testing and quality
Backend unit/contract/integration tests (pytest), frontend unit tests (vitest), lint/typecheck/build, a Playwright five-question journey and a 10-route × 2-width × 2-theme visual/accessibility sweep. Executed commands and results: `docs/TEST_EVIDENCE.md`.

## 8. Limitations
Synthetic, compositional text is cleaner than real comments; the audit set and gloss were written by the same author as the templates; cluster names come from a keyword labeller; silhouette is low in absolute terms on sentence embeddings; the observed data is YouTube-only with withheld text and missing comment dates; no live Instagram/TikTok/Facebook connectors; all comparisons are associational; anomalies are statistical outliers, not evidence of fraud.

## 9. Future work
Collect a permitted real corpus (owner YouTube key; brand-owned Instagram/TikTok exports) and have three native speakers label a stratified sample in all three languages; re-run the unchanged selection rule on it; replace the gloss with a learned Roman-Urdu→Urdu transliteration model; add a durable hosted store for imports; run the suggested A/B tests to obtain causal evidence.

## 10. Contribution map
| Part | Source |
|---|---|
| YouTube client, null-safe metrics, statistics, language ID, keyword-matcher technique, card anatomy, number-locked wording | Project 1 (Content Detective), adapted |
| Next.js + FastAPI Vercel layout, shell/UI patterns, CSV header mapping, CSV-injection guard, public-demo guard | SignalSpend, adapted |
| Multi-platform post schema, synthetic multilingual corpus, comment clustering + selection + profiling, Roman-Urdu gloss, peer-cohort anomalies, need-linked recommendations, all ten UI views | New for Project 3 |

## 11. Reproduce
README → *Local setup*, *Tests*. `python pipelines/build_demo.py` regenerates the dataset (seed 42); `python pipelines/report_evaluation.py` regenerates the evaluation and provenance documents from it.
