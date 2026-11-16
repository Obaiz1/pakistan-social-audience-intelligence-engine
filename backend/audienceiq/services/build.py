"""End-to-end dataset build: normalise → enrich comments → embed → cluster → anomalies → recommendations → tables.

Used by the offline pipelines (semantic embeddings) and by CSV imports (lexical embeddings, bounded size).
"""

import json
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from audienceiq.analytics.content import compare
from audienceiq.analytics.engagement import add_engagement
from audienceiq.anomalies.detect import detect
from audienceiq.clustering.pipeline import run_clustering
from audienceiq.constants import IMPORTED_DISCLAIMER, OBSERVED_DISCLAIMER, SYNTHETIC_DISCLAIMER
from audienceiq.nlp.embeddings import LEXICAL_NAME, LexicalEmbedder, hybrid
from audienceiq.nlp.gloss import embedding_text
from audienceiq.nlp.intent import label_need, purchase_intent, sentiment
from audienceiq.nlp.langid import detect_language
from audienceiq.nlp.normalize import normalize_text, strip_boilerplate
from audienceiq.recommendations.engine import build_recommendations
from audienceiq.recommendations.engine import to_rows as rec_rows

DISCLAIMERS = {"synthetic": SYNTHETIC_DISCLAIMER, "observed": OBSERVED_DISCLAIMER, "imported": IMPORTED_DISCLAIMER}
RUNTIME_K = [4, 5, 6, 7, 8, 9, 10, 12]


@dataclass
class BuildConfig:
    dataset_id: str
    name: str
    mode: str                                  # synthetic | observed | imported
    description: str
    product_category: str
    snapshot_at: str
    text_permission: str                       # full | illustrative | withheld
    sources: list[dict]
    seed: int = 42
    generator_version: str | None = None
    expires_at: str | None = None
    embedding: str = "lexical"                 # lexical | semantic | hybrid | compare (offline: all three)
    semantic_encoder: object | None = None     # callable(list[str]) -> np.ndarray (offline only)
    semantic_model: str = ""
    k_values: list[int] = field(default_factory=lambda: list(RUNTIME_K))
    hdbscan_sizes: list[int] = field(default_factory=list)
    hdbscan_reducer: str = "pca"
    truth: dict[str, np.ndarray] | None = None
    preferred_embedding: str | list[str] | None = None


def enrich_comments(comments: pd.DataFrame, text_permission: str, source: str) -> pd.DataFrame:
    c = comments.copy()
    c["comment_text"] = c["comment_text"].fillna("").astype(str)
    c["norm_text"] = c["comment_text"].map(normalize_text)
    c["display_text"] = c["norm_text"].map(strip_boilerplate)
    c["language_type"] = c["comment_text"].map(detect_language)
    c["embed_text"] = [embedding_text(t, lg) for t, lg in zip(c["display_text"], c["language_type"], strict=True)]
    labels = [label_need(None, t) for t in c["norm_text"]]
    c["topic"] = [lab.topic for lab in labels]
    c["topic_confidence"] = [lab.confidence for lab in labels]
    c["sentiment"] = [sentiment(None, t) for t in c["norm_text"]]
    c["purchase_intent"] = [purchase_intent(None, t, lab) for t, lab in zip(c["norm_text"], labels, strict=True)]
    c["char_len"] = c["comment_text"].str.len().astype(int)
    c["text_permission"] = text_permission
    c["source"] = source
    if "like_count" not in c:
        c["like_count"] = pd.NA
    if "published_at" not in c:
        c["published_at"] = None
    return c


def _step(log: list, step: str, started: float, **details) -> float:
    now = time.time()
    log.append({"step": step, "status": "ok", "seconds": round(now - started, 2), **details})
    return now


def build_dataset(posts: pd.DataFrame, comments: pd.DataFrame, campaigns: pd.DataFrame, cfg: BuildConfig) -> dict:
    """Return {'dataset': row dict, 'tables': {...canonical tables...}, 'evaluation': {...}}."""
    log: list[dict] = []
    t = time.time()
    created = datetime.now(UTC).isoformat(timespec="seconds")
    src = cfg.sources[0]
    p = posts.copy()
    p["dataset_id"] = cfg.dataset_id
    p["snapshot_at"] = cfg.snapshot_at
    for col, default in [("source_id", src["source_id"]), ("source_type", src["source_type"]),
                         ("dataset_origin", cfg.mode), ("collection_method", src["collection_method"]),
                         ("reuse_permission", src["reuse_permission"]),
                         ("observed_vs_synthetic", {"synthetic": "synthetic", "observed": "observed"}.get(cfg.mode, "imported")),
                         ("source_url", None), ("content_type_raw", None), ("post_text", None), ("campaign_id", None)]:
        if col not in p:
            p[col] = default
        else:
            p[col] = p[col].where(p[col].notna(), default) if default is not None else p[col]
    if "source_post_id" not in p:
        p["source_post_id"] = p["post_id"]
    camp = campaigns.copy() if campaigns is not None and len(campaigns) else pd.DataFrame(columns=["campaign_id"])
    if len(camp):
        camp["dataset_id"] = cfg.dataset_id
    t = _step(log, "normalize_posts", t, posts=len(p))

    c = enrich_comments(comments, cfg.text_permission, src["source_type"])
    c["dataset_id"] = cfg.dataset_id
    t = _step(log, "enrich_comments", t, comments=len(c))

    texts = c["embed_text"].tolist()
    embeddings: dict[str, tuple[np.ndarray, str]] = {}
    lexical = LexicalEmbedder(seed=cfg.seed)
    lex = lexical.fit_transform(texts) if len(texts) else np.zeros((0, 2))
    if cfg.embedding in {"lexical", "compare"}:
        embeddings["lexical"] = (lex, LEXICAL_NAME)
    sem = None
    if cfg.embedding in {"semantic", "hybrid", "compare"}:
        if cfg.semantic_encoder is None:
            raise ValueError("semantic embeddings requested but no encoder supplied (offline pipeline only)")
        sem = cfg.semantic_encoder(texts)
        if cfg.embedding in {"semantic", "compare"}:
            embeddings["semantic"] = (sem, cfg.semantic_model)
        if cfg.embedding in {"hybrid", "compare"}:
            embeddings["hybrid"] = (hybrid(sem, lex), f"0.6·{cfg.semantic_model} ⊕ 0.4·{LEXICAL_NAME}")
    t = _step(log, "embed", t, representations=list(embeddings))

    show_text = cfg.text_permission in {"full", "illustrative"}
    clu = run_clustering(c[["comment_id", "comment_text", "norm_text", "language_type", "topic", "published_at"]]
                         .assign(norm_text=c["display_text"]), cfg.dataset_id, embeddings, cfg.k_values,
                         cfg.hdbscan_sizes, seed=cfg.seed, show_text=show_text, truth=cfg.truth,
                         preferred=cfg.preferred_embedding, hdbscan_reducer=cfg.hdbscan_reducer)
    t = _step(log, "cluster", t, candidates=len(clu.runs), selected=clu.evaluation["selected_key"])

    enriched = add_engagement(p)
    need_by_cluster = {pr["cluster_id"]: pr["need_category"] for pr in clu.profiles}
    cn = c[["comment_id", "post_id"]].assign(need=[need_by_cluster.get(int(x)) for x in clu.labels])
    anomalies = detect(enriched, cn, dataset_id=cfg.dataset_id)
    t = _step(log, "anomalies", t, flagged=anomalies["metrics"]["posts_flagged"])

    content_cmp = compare(enriched, "content_type", "attention_index")
    clustered = cn.merge(enriched[["post_id", "campaign", "brand", "platform", "content_type"]], on="post_id")
    clustered = clustered[clustered["need"].notna() & (clustered["need"] != "noise")]
    n_clustered = int((clu.labels != -1).sum())
    recs = build_recommendations(clu.profiles, n_clustered, clustered, content_cmp, anomalies["flags"], enriched,
                                 cfg.dataset_id, cfg.mode)
    t = _step(log, "recommendations", t, cards=len(recs))

    stored_comments = c.drop(columns=["norm_text", "embed_text", "display_text"])
    if not show_text:
        stored_comments["comment_text"] = None
        # date-only timestamps for withheld datasets (a full timestamp + video could single out a commenter)
        stored_comments["published_at"] = stored_comments["published_at"].astype(str).str.slice(0, 10).where(
            stored_comments["published_at"].notna(), None)
    dataset = {
        "dataset_id": cfg.dataset_id, "name": cfg.name, "mode": cfg.mode, "description": cfg.description,
        "product_category": cfg.product_category, "created_at": created, "snapshot_at": cfg.snapshot_at,
        "expires_at": cfg.expires_at, "seed": cfg.seed, "generator_version": cfg.generator_version,
        "text_permission": cfg.text_permission, "disclaimer": DISCLAIMERS[cfg.mode], "post_count": int(len(p)),
        "comment_count": int(len(c)), "sources": cfg.sources,
    }
    run_id = clu.selected["run_id"]
    pipeline_rows = pd.DataFrame([{"run_id": run_id, "dataset_id": cfg.dataset_id, "step": s["step"], "status": s["status"],
                                   "started_at": created, "finished_at": created,
                                   "details_json": json.dumps({k: v for k, v in s.items() if k not in {"step", "status"}},
                                                              default=str)} for s in log])
    evaluation = {"clustering": clu.evaluation, "anomalies": anomalies["metrics"], "pipeline": log,
                  "nlp": nlp_summary(c)}
    tables = {
        "campaigns": camp, "posts": p, "comments": stored_comments, "cluster_runs": clu.runs,
        "cluster_assignments": clu.assignments, "cluster_profiles": clu.profile_rows,
        "anomaly_runs": pd.DataFrame([anomalies["run"]]), "anomaly_flags": anomalies["flags"],
        "anomaly_scores": anomalies["scores"], "recommendations": rec_rows(recs), "pipeline_runs": pipeline_rows,
    }
    return {"dataset": dataset, "tables": tables, "evaluation": evaluation, "clustering": clu, "comments": c,
            "lexical": lexical, "posts_enriched": enriched, "anomalies": anomalies}


def nlp_summary(c: pd.DataFrame) -> dict:
    return {"language_mix": c["language_type"].value_counts().to_dict(),
            "reference_topic_mix": c["topic"].value_counts().to_dict(),
            "reference_unlabelled_share": round(float((c["topic"] == "other").mean()), 4) if len(c) else None,
            "purchase_intent_mix": c["purchase_intent"].value_counts().to_dict(),
            "sentiment_mix": c["sentiment"].value_counts().to_dict()}


def bundle_path(data_dir: Path, dataset_id: str) -> Path:
    return data_dir / "datasets" / dataset_id
