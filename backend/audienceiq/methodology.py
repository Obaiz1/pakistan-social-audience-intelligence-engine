"""Methodology content served at /api/v1/methodology: assignment mapping, formulas, models, data, limitations."""

import json

from audienceiq.analytics.engagement import FORMULAS, MATURE_DAYS
from audienceiq.anomalies import detect as anomaly
from audienceiq.clustering import pipeline as clustering
from audienceiq.constants import PRODUCT_NAME, PROJECT_TITLE, SHORT_NAME
from audienceiq.recommendations import engine as rec

QUESTIONS = [
    {"id": "Q1", "question": "Which content attracts attention?", "route": "/content",
     "method": "Platform-specific engagement formulas; attention index vs brand × platform baseline; medians with bootstrap "
               "95% CIs, Mann-Whitney vs rest, Cliff's δ, Benjamini–Hochberg; immature posts excluded."},
    {"id": "Q2", "question": "What does the audience want?", "route": "/audience",
     "method": "Comments normalised (Unicode, Urdu letter forms, Roman-Urdu spelling variants, PII stripped), embedded with a "
               "multilingual sentence model, and grouped by unsupervised clustering; groups named afterwards."},
    {"id": "Q3", "question": "Which marketing patterns are unusual?", "route": "/anomalies",
     "method": "Peer-cohort robust z-scores (median/MAD) on engagement and comments-per-like, binomial test on discovered-need "
               "mix, Isolation Forest as a secondary multivariate score."},
    {"id": "Q4", "question": "Which audience needs should the brand address?", "route": "/audience",
     "method": "Cluster profiles: size, share, language mix, campaign/brand/platform lift, exemplars, cohesion, name agreement, "
               "date range and caveats."},
    {"id": "Q5", "question": "What should the marketing team do next?", "route": "/recommendations",
     "method": "Deterministic cards from gated evidence (cluster support, significant lift, significant content effects, "
               "recurring anomalies) with sample sizes, limitations and an A/B or service test."},
]


def methodology_payload(f) -> dict:
    sel = f.selected_run or {}
    ev = f.evaluation or {}
    clu = ev.get("clustering", {})
    return {
        "project_title": PROJECT_TITLE, "product_name": PRODUCT_NAME, "short_name": SHORT_NAME,
        "questions": QUESTIONS,
        "dataset": {"name": f.meta["name"], "mode": f.meta["mode"], "disclaimer": f.meta["disclaimer"],
                    "posts": f.meta["post_count"], "comments": f.meta["comment_count"],
                    "snapshot_at": f.meta["snapshot_at"], "seed": f.meta.get("seed"),
                    "generator_version": f.meta.get("generator_version"), "sources": f.meta.get("sources", []),
                    "text_permission": f.meta["text_permission"], "description": f.meta.get("description")},
        "engagement": {"formulas": FORMULAS, "mature_days": MATURE_DAYS,
                       "attention_index": "interactions / median interactions of mature posts of the same brand × platform",
                       "weighted_er": "Σ interactions / Σ views over posts reporting both (not an average of ratios)",
                       "missing_values": "Null means not reported and is never replaced by zero."},
        "clustering": {"selected": {"run_id": sel.get("run_id"), "embedding": sel.get("embedding"),
                                    "embedding_model": sel.get("embedding_model"), "algorithm": sel.get("algorithm"),
                                    "params": json.loads(sel.get("params_json") or "{}"), "n_clusters": sel.get("n_clusters"),
                                    "noise_rate": sel.get("noise_rate"), "metrics": json.loads(sel.get("metrics_json") or "{}")},
                       "selection_rule": clu.get("selection_rule", {"max_noise": clustering.MAX_NOISE,
                                                                    "min_cluster_share": clustering.MIN_CLUSTER_SHARE,
                                                                    "max_k": clustering.MAX_K}),
                       "candidates": len(f.cluster_runs), "audit": ev.get("audit"), "synthetic_recovery": ev.get("synthetic_recovery"),
                       "naming": "Majority vote of a multilingual keyword reference labeller over cluster members; agreement "
                                 "share reported; < 45% → 'Mixed'."},
        "anomalies": {"min_cohort": anomaly.MIN_COHORT, "z_threshold": anomaly.Z_THRESHOLD, "high_z": anomaly.HIGH_Z,
                      "mix_alpha": anomaly.MIX_ALPHA, "iforest_top": anomaly.IFOREST_TOP, "caveat": anomaly.CAVEAT,
                      "evaluation": ev.get("anomaly_recovery")},
        "recommendations": {"min_agreement": rec.MIN_AGREEMENT, "min_support": rec.MIN_SUPPORT, "min_share": rec.MIN_SHARE,
                            "min_lift": rec.MIN_LIFT, "alpha": rec.ALPHA, "min_flags": rec.MIN_FLAGS,
                            "llm": "Optional number-locked rewording only (off by default, never on the public demo)."},
        "nlp": ev.get("nlp", {}), "langid_evaluation": ev.get("langid"),
        "limitations": [
            "The synthetic corpus demonstrates the method; it is not evidence about any real brand or audience.",
            "Observed YouTube data covers Pakistan-related brand channels; viewer location is not verified.",
            "Instagram/TikTok/Facebook data can only enter through authorised exports (CSV import); no live connectors.",
            "Clustering quality on synthetic text overstates real-world quality; see the audit on independently written comments.",
            "Rule-based reference labels name clusters and can be wrong, especially for code-switched or sarcastic text.",
            "All comparisons are associational; campaigns, budgets and seasons are confounded.",
            "Anomalies are statistical outliers, not evidence of fraud, bots or paid activity.",
        ],
        "reproducibility": [
            "python -m venv .venv && pip install -e \".[dev,ml]\"",
            "python pipelines/build_demo.py   # seed 42 → data/datasets/synthetic-lawn-demo-v1",
            "python -m pytest -q",
            "uvicorn audienceiq.api.app:app --app-dir backend --port 8000",
            "npm --prefix frontend ci && npm --prefix frontend run dev",
        ],
        "upstream": [
            {"repo": "Obaiz1/pakistani-social-media-content-detective", "commit": "957e3b6f",
             "reused": "YouTube client, null-safe metrics, statistics (bootstrap/Mann-Whitney/Cliff's δ/BH), language ID, "
                       "keyword-matcher technique, recommendation-card anatomy, number-locked LLM wording"},
            {"repo": "Obaiz1/signalspend-ai", "commit": "9c5f4152",
             "reused": "Next.js + FastAPI single-project Vercel layout, shell/UI patterns and theme tokens, CSV header mapping "
                       "and strict number parsing, CSV-injection guard, public-demo write guard"},
        ],
        "new_in_project3": ["Comment-level multilingual embeddings and unsupervised clustering with model selection",
                            "Cluster profiling and post-hoc naming with agreement", "Peer-cohort post anomaly detection",
                            "Need-linked recommendation engine", "Multi-platform post schema and synthetic classroom corpus"],
    }
