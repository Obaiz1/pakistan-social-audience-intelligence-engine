# Architecture

```
Browser ──► Next.js 16 App Router (frontend/, React 19, Tailwind 4, Recharts 3)
              │  typed client lib/api.ts · URL-backed filters · chart⇄table parity · dark/light
              │  same-origin /api/v1/*   (dev: next.config.ts rewrite → 127.0.0.1:8000 · Vercel: vercel.json rewrite)
              ▼
           FastAPI (backend/audienceiq/api/app.py) — one Python function on Vercel (frontend/api/index.py)
              │  read-only public demo guard · size/origin checks · Pydantic contracts · meta envelope on every result
              ▼
           Repository (storage/repository.py)
              │  built-in bundles: data/datasets/<id>/*.csv ──► in-memory SQLite (schema.sql, FKs/CHECKs/UNIQUE)
              │  local user imports: var/audienceiq_user.sqlite (git-ignored; disabled when hosted)
              ▼
           pandas frames per dataset (cached) ──► request-time analytics with filters
                 analytics/engagement.py · analytics/content.py (Q1) · comments_clustered join (Q2/Q4)
                 anomaly_flags/scores (Q3) · recommendations (Q5) · reports/export.py · data/quality.py

Offline (never on Vercel)                              pipelines/build_demo.py · pipelines/collect_youtube.py
   synthetic generator / YouTube API / CSV import
   → nlp/normalize, langid, intent (reference labels)
   → nlp/embeddings: semantic (mpnet, torch) · lexical (TF-IDF+SVD) · hybrid
   → clustering/pipeline: KMeans sweep + UMAP/PCA-HDBSCAN → ADR-007 selection → profiles
   → anomalies/detect → recommendations/engine → storage/db.write_bundle_dir (CSV + SHA-256 manifest)
```

## Why this shape
- **One Vercel project, same origin.** Repo B proved the layout in production (2026-11-02) with the same Next/React versions; no CORS, one URL (ADR-002).
- **Heavy ML offline.** Sentence embeddings need torch; the deployed function only reads versioned tables, keeping the bundle well below Vercel's 500 MB Python limit and making every request fast and deterministic (ADR-003).
- **Canonical store re-validated on every cold start.** CSV bundles are diff-able and openable in Excel; loading them through `schema.sql` re-checks keys, uniqueness and CHECK constraints (ADR-004).
- **Runtime path for user data.** CSV imports run the same pipeline with the lexical baseline (scikit-learn only), bounded in size, and persist locally.

## Module map (backend/audienceiq)
| Module | Responsibility |
|---|---|
| `constants.py`, `config.py` | Vocabularies, disclaimers; env settings (hosted/read-only, upload limit) |
| `data/synthetic.py`, `synthetic_text.py` | Seed-42 classroom corpus (posts, multilingual comments, injected anomalies + truth) |
| `data/youtube.py`, `youtube_adapter.py` | Repo A API client; mapping to post/comment schema |
| `data/importer.py`, `data/quality.py` | CSV preview/mapping/validation; dataset quality audit |
| `nlp/` | Normalisation, language ID, reference need labeller, embeddings |
| `clustering/` | Candidates, metrics, selection pipeline, profiles/naming |
| `analytics/` | Engagement formulas, Repo A statistics, Q1 comparisons |
| `anomalies/detect.py` | Peer-cohort robust z, comment ratio, need-mix test, Isolation Forest |
| `recommendations/` | Evidence-gated cards; optional number-locked wording |
| `services/` | Build orchestration; synthetic/import/observed dataset factories |
| `storage/` | Schema, bundle IO, repository |
| `api/` | FastAPI app, contracts, helpers |
| `reports/export.py`, `methodology.py` | Exports, methodology payload |

## Frontend map (frontend/)
`app/<route>/page.tsx` (server shells, each wrapping a client view in `<Suspense>` because the views read URL search params) → `components/views/*.tsx` (one per route) → shared `components/{shell,dataset,filters,charts,ui}.tsx` → `lib/{api,types,query,format}.ts`.
