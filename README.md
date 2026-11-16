# Pakistan Audience & Campaign Intelligence (AudienceIQ PK)

**University Project 3 — _Pakistan Social Audience & Campaign Intelligence Engine (Clustering Based)_**

A web application that groups multilingual social-media comments (English, Roman Urdu, Urdu) into audience-need clusters, finds posts that behave unusually compared with their peers, and turns both into evidence-linked marketing recommendations for a Pakistani women's lawn-suit brand.

> **Data status:** the public demo runs on a deterministic **SYNTHETIC classroom dataset** ({{TBD_POSTS}} posts, {{TBD_COMMENTS}} comments, seed 42, fictional brands). It is labelled on every page, API response and export. An observed YouTube collector is implemented but not run in this build (needs the owner's API key — see [Limitations](#known-limitations-and-blocked-items)).

**Live app:** {{TBD_URL}} · **Repository:** {{TBD_REPO}}

## The five questions and where they are answered
| # | Question | Page | Method (one line) |
|---|---|---|---|
| Q1 | Which content attracts attention? | `/content`, `/campaigns` | Platform-specific engagement formulas; attention index vs brand × platform baseline; medians, bootstrap CIs, Mann-Whitney + Cliff's δ + BH |
| Q2 | What does the audience want? | `/audience`, `/comments` | Multilingual sentence embeddings → KMeans/HDBSCAN candidates → rule-based model selection → post-hoc naming with agreement |
| Q3 | Which marketing patterns are unusual? | `/anomalies` | Peer-cohort robust z (median/MAD), comments-per-like, need-mix binomial test, Isolation Forest (secondary) |
| Q4 | Which audience needs should the brand address? | `/audience` (needs by campaign), `/campaigns` | Cluster profiles: size, share, language mix, campaign/platform lift, exemplars, caveats |
| Q5 | What should the marketing team do next? | `/recommendations` | Deterministic cards from gated evidence, each with sample size, limitations and an A/B or service test |

The overview page has a guided **"Try this project"** path through Q1–Q5. `/data` (provenance, quality audit, CSV import), `/reports` (CSV/Excel/PDF) and `/methodology` (official title, formulas, model comparison, audit, limitations) complete the app.

## Headline results on the synthetic demo
{{TBD_RESULTS}}

These numbers describe a simulation designed to contain discoverable structure; they are **not** findings about real brands or audiences. See `docs/CLUSTERING_EVALUATION.md` and `docs/PROJECT3_FINAL_REPORT.md`.

## Tech stack
- **Frontend:** Next.js 16.4 (App Router), React 19.3, TypeScript 5.9, Tailwind CSS 4.3, Recharts 3.10, lucide-react; vitest; Playwright for E2E/visual QA.
- **Backend:** Python 3.12, FastAPI 0.121, pydantic 2.12, pandas 2.3, NumPy 2.3, SciPy 1.16, scikit-learn 1.7, fpdf2, openpyxl. SQLite canonical store.
- **Offline ML (not deployed):** sentence-transformers 5 + torch (CPU), `paraphrase-multilingual-mpnet-base-v2` (Apache-2.0), umap-learn.
- **Hosting:** Vercel (Next.js + Python function in one project, layout reused from SignalSpend).

## Local setup
Requires Python 3.12, Node 24 (npm 11). The committed dataset bundle means **no API key and no ML install are needed** to run the app.

**Windows PowerShell**
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn audienceiq.api.app:app --app-dir backend --port 8000     # terminal 1
npm --prefix frontend ci
npm --prefix frontend run dev                                     # terminal 2 → http://127.0.0.1:3000
```

**macOS / Linux**
```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn audienceiq.api.app:app --app-dir backend --port 8000 &
npm --prefix frontend ci && npm --prefix frontend run dev
```

Rebuild the synthetic bundle (optional, needs the ML extra and ~1 GB model download):
```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -e ".[dev,ml]" umap-learn
python pipelines/build_demo.py          # seed 42 → data/datasets/synthetic-lawn-demo-v1/
python pipelines/build_demo.py --embedding lexical   # no torch: lexical baseline only
```

Collect observed YouTube data (optional, your own key; raw text stays in git-ignored `data/observed/private/`):
```bash
export YOUTUBE_API_KEY=...              # PowerShell: $env:YOUTUBE_API_KEY="..."
python pipelines/collect_youtube.py --months 24
```

## Tests
```bash
python -m ruff check backend pipelines
python -m pytest -q                      # backend: unit, contract, integration
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend test               # vitest
npm --prefix frontend run build
APP_URL=http://127.0.0.1:3000 node frontend/e2e/journey.mjs   # five-question browser journey
APP_URL=http://127.0.0.1:3000 node frontend/e2e/screens.mjs   # 10 routes × 375/1440 × dark/light
```
Latest executed results: `docs/TEST_EVIDENCE.md`.

## Keys and environment
None are required. Optional names are documented in `.env.example`: `YOUTUBE_API_KEY` (collector only), `NVIDIA_API_KEY` + `AUDIENCEIQ_ENABLE_LLM` (local, number-locked wording only), `AUDIENCEIQ_HOSTED`, `AUDIENCEIQ_ALLOW_WRITES`, `AUDIENCEIQ_MAX_UPLOAD_BYTES`, `API_ORIGIN`. Secrets live in `.env` (git-ignored) or the Vercel/GitHub secret stores.

## Data sourcing
- **Synthetic (shipped):** `backend/audienceiq/data/synthetic.py`, seed 42, fictional "Brand A–F", invented comment texts, injected anomalies with separate ground truth. Provenance and exact counts: `docs/DATA_PROVENANCE.md`.
- **Observed (optional):** YouTube Data API v3, official channels pinned by ID (from Project 1's audit). Comment text is never redistributed; observed bundles expire after 30 days.
- **Imported:** your own CSV exports (Instagram/TikTok/Facebook insights, etc.) via `/data`, with field mapping, validation and a source attestation. There are no live Instagram/TikTok/Facebook connectors.
- **Assignment sources checked:** the 2026 paper provides no downloadable data/code; the e-commerce dataset is transactions, not comments; the fashion catalogue has an unclear licence and a different category — none were used (`docs/assignment/PROJECT3_REQUIREMENTS.md`).

## Known limitations and blocked items
{{TBD_LIMITATIONS}}

## Documentation
[Upstream audit](docs/UPSTREAM_AUDIT.md) · [Traceability](docs/TRACEABILITY_MATRIX.md) · [Architecture](docs/ARCHITECTURE.md) · [Decisions](docs/DECISIONS.md) · [Data dictionary](docs/DATA_DICTIONARY.md) · [Provenance](docs/DATA_PROVENANCE.md) · [Clustering evaluation](docs/CLUSTERING_EVALUATION.md) · [Anomaly method](docs/ANOMALY_METHOD.md) · [Methodology](docs/METHODOLOGY.md) · [Final report](docs/PROJECT3_FINAL_REPORT.md) · [Test evidence](docs/TEST_EVIDENCE.md) · [QA checklist](docs/QA_CHECKLIST.md) · [Deployment](docs/DEPLOYMENT.md) · [Demo script & viva](docs/DEMO_SCRIPT_AND_VIVA.md) · [Progress](docs/PROGRESS.md) · [Handoff](docs/SESSION_HANDOFF.md)

## Credits and reuse
Built on two earlier projects by the same author: [pakistani-social-media-content-detective](https://github.com/Obaiz1/pakistani-social-media-content-detective) (@957e3b6f) and [signalspend-ai](https://github.com/Obaiz1/signalspend-ai) (@9c5f4152). Reused files carry provenance headers; the reuse table is in `docs/UPSTREAM_AUDIT.md`. Built with AI assistance (Claude Code) under the author's direction.
