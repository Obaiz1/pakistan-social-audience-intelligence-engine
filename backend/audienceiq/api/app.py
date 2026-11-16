"""AudienceIQ PK — FastAPI application (/api/v1). All numbers are computed here; the frontend only renders them."""

import os
import re
from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response

from audienceiq import __version__
from audienceiq.analytics.content import campaign_analysis, compare, content_analysis, needs_by, weighted_er
from audienceiq.analytics.engagement import FORMULAS, MATURE_DAYS, coverage
from audienceiq.api import schemas
from audienceiq.api.common import (
    Filters,
    clean,
    filtered_posts,
    filters_dep,
    frame_records,
    load_frames,
    loads,
    meta,
    paginate,
)
from audienceiq.config import get_settings
from audienceiq.constants import CONTENT_TYPE_LABELS, LANGUAGE_LABELS, NEED_LABELS, PRODUCT_NAME, SHORT_NAME
from audienceiq.data import importer
from audienceiq.data.quality import quality_report
from audienceiq.methodology import methodology_payload
from audienceiq.reports import export
from audienceiq.storage.repository import get_repository

app = FastAPI(title=f"{SHORT_NAME} API", version=__version__, docs_url="/api/v1/docs", openapi_url="/api/v1/openapi.json",
              redoc_url=None)
V1 = "/api/v1"
READ_ONLY_POSTS = {f"{V1}/imports/preview"}


@app.middleware("http")
async def guard(request: Request, call_next):
    s = get_settings()
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        length = int(request.headers.get("content-length") or 0)
        if length > s.max_upload_bytes * 2 + 65_536:
            return JSONResponse(status_code=413, content={"detail": f"Request too large (limit {s.max_upload_bytes:,} bytes "
                                                                    "per CSV)."})
        origin = request.headers.get("origin")
        host = request.headers.get("host", "")
        if origin and not re.match(rf"^https?://{re.escape(host)}$", origin) and not origin.startswith(
                ("http://127.0.0.1", "http://localhost")):
            return JSONResponse(status_code=403, content={"detail": "Cross-site writes are not allowed."})
        if not s.writes_enabled and request.url.path not in READ_ONLY_POSTS:
            return JSONResponse(status_code=403, content={
                "detail": "The public demo is read-only: datasets cannot be created, imported or deleted here. CSV preview "
                          "and validation still work. Run the app locally (see README) to persist imports."})
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = response.headers.get("Cache-Control", "no-store")
    return response


@app.exception_handler(importer.ImportError_)
async def import_error(_request: Request, exc: importer.ImportError_):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


# ---------------------------------------------------------------- health & datasets
@app.get(f"{V1}/health", response_model=schemas.Health)
def health():
    s = get_settings()
    problems = []
    try:
        repo = get_repository()
        datasets = repo.list_datasets()
        default = repo.default_dataset_id()
    except Exception as exc:  # report, never crash the health check
        datasets, default = [], None
        problems.append(f"storage: {type(exc).__name__}")
    if not datasets:
        problems.append("no datasets loaded")
    return {"status": "ok" if not problems else "degraded", "app": PRODUCT_NAME, "version": __version__,
            "api_version": "v1", "environment": s.app_env, "hosted": s.hosted, "writes_enabled": s.writes_enabled,
            "llm_enabled": s.llm_enabled, "datasets": len(datasets), "default_dataset_id": default,
            "build_commit": (os.environ.get("VERCEL_GIT_COMMIT_SHA") or os.environ.get("AUDIENCEIQ_BUILD_COMMIT") or None),
            "storage": {"builtin": "in-memory SQLite loaded from committed CSV bundles (read-only)",
                        "user_store": "disabled (hosted, read-only)" if not s.writes_enabled else "local SQLite file (var/)"},
            "time": datetime.now(UTC).isoformat(timespec="seconds"), "problems": problems}


@app.get(f"{V1}/datasets", response_model=schemas.DatasetList)
def datasets():
    repo = get_repository()
    return {"datasets": repo.list_datasets(), "default_dataset_id": repo.default_dataset_id(),
            "writes_enabled": get_settings().writes_enabled}


@app.delete(f"{V1}/datasets/{{dataset_id}}")
def delete_dataset(dataset_id: str):
    try:
        get_repository().delete_user_dataset(dataset_id)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from None
    except KeyError:
        raise HTTPException(404, f"Dataset '{dataset_id}' not found.") from None
    return {"deleted": dataset_id}


@app.post(f"{V1}/datasets/demo")
def demo(req: schemas.DemoRequest):
    from audienceiq.services.datasets import build_synthetic

    ds = build_synthetic(n_posts=req.n_posts, seed=req.seed, embedding="lexical", persist_user=True)
    return {"dataset_id": ds["dataset_id"], "posts": ds["post_count"], "comments": ds["comment_count"],
            "note": "Regenerated with the runtime lexical embedding (the shipped demo uses offline semantic embeddings)."}


@app.get(f"{V1}/options")
def options(dataset_id: str | None = None):
    """Filter vocabularies for the selected dataset (values that actually occur)."""
    f = load_frames(dataset_id)
    p = f.posts
    published = pd.to_datetime(p["published_at"], utc=True)
    return {"meta": meta(f, len(p)), "platforms": sorted(p["platform"].unique().tolist()),
            "brands": sorted(p["brand"].unique().tolist()), "campaigns": sorted(p["campaign"].unique().tolist()),
            "content_types": [{"value": c, "label": CONTENT_TYPE_LABELS.get(c, c)} for c in sorted(p["content_type"].unique())],
            "languages": [{"value": c, "label": LANGUAGE_LABELS.get(c, c)} for c in sorted(f.comments["language_type"].unique())],
            "topics": [{"value": c, "label": NEED_LABELS.get(c, c)} for c in sorted(f.comments["topic"].unique())],
            "clusters": [{"value": int(r["cluster_id"]), "label": f"#{int(r['cluster_id'])} {r['label']}"}
                         for r in f.profiles.sort_values("cluster_id").to_dict(orient="records")],
            "date_min": str(published.min())[:10], "date_max": str(published.max())[:10]}


# ---------------------------------------------------------------- posts
SORTABLE = {"published_at", "likes", "comments_count", "shares", "views", "er_views", "attention_index", "days_since_post"}


@app.get(f"{V1}/posts")
def posts(dataset_id: str | None = None, filters: Filters = Depends(filters_dep),
          sort: str = Query("published_at"), order: str = Query("desc", pattern="^(asc|desc)$"),
          page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=200), q: str | None = Query(None, max_length=80)):
    if sort not in SORTABLE:
        raise HTTPException(422, f"sort must be one of {sorted(SORTABLE)}")
    f = load_frames(dataset_id)
    df = filtered_posts(f, filters)
    if q:
        df = df[df["post_id"].str.contains(q, case=False, regex=False) | df["campaign"].str.contains(q, case=False, regex=False)]
    flagged = set(f.flags["post_id"])
    df = df.sort_values(sort, ascending=order == "asc", na_position="last")
    chunk, pg = paginate(df, page, page_size)
    cols = ["post_id", "brand", "platform", "campaign", "content_type", "product_category", "likes", "comments_count",
            "shares", "views", "days_since_post", "published_at", "interactions", "er_views", "er_formula",
            "attention_index", "mature", "source_url", "source_type", "observed_vs_synthetic"]
    rows = frame_records(chunk, cols)
    for r in rows:
        r["flagged"] = r["post_id"] in flagged
    return {"meta": meta(f, len(df), filters), "page": pg, "rows": rows}


@app.get(f"{V1}/posts/{{post_id}}")
def post_detail(post_id: str, dataset_id: str | None = None):
    f = load_frames(dataset_id)
    row = f.posts[f.posts["post_id"] == post_id]
    if row.empty:
        raise HTTPException(404, f"Post '{post_id}' not found in this dataset.")
    cc = f.comments_clustered
    com = cc[cc["post_id"] == post_id]
    comments = frame_records(com, ["comment_id", "comment_text", "language_type", "topic", "sentiment", "purchase_intent",
                                   "cluster_id", "cluster_label", "need", "published_at"])
    return {"meta": meta(f, 1), "post": frame_records(row)[0], "comments": comments,
            "comments_note": None if f.meta["text_permission"] != "withheld" else "Comment text is withheld for this dataset.",
            "flags": frame_records(f.flags[f.flags["post_id"] == post_id]),
            "need_mix": com["need"].value_counts().to_dict()}


# ---------------------------------------------------------------- analytics (Q1)
@app.get(f"{V1}/analytics/overview")
def overview(dataset_id: str | None = None, filters: Filters = Depends(filters_dep)):
    f = load_frames(dataset_id)
    p = filtered_posts(f, filters)
    cc = _cc_filtered(f, p)
    mature = p[p["mature"]]
    by_platform = [{"platform": k, "posts": int(len(g)), "weighted_er": clean(weighted_er(g[g["mature"]])),
                    "formula": FORMULAS.get(k)} for k, g in p.groupby("platform")]
    content = compare(p, "content_type", "attention_index")
    clusters = _cluster_rows(f, cc)
    top_clusters = [c for c in clusters if c["cluster_id"] != -1][:5]
    fl = f.flags[f.flags["post_id"].isin(set(p["post_id"]))].copy()
    fl["abs"] = fl["score"].abs()
    top_flags = fl.sort_values(["severity", "abs"], ascending=[True, False]).head(3)
    recs = [_rec(r) for r in f.recommendations.to_dict(orient="records")][:3]
    published = pd.to_datetime(p["published_at"], utc=True)
    return {
        "meta": meta(f, len(p), filters, f.selected_run),
        "kpis": {"posts": int(len(p)), "posts_mature": int(len(mature)), "comments": int(len(cc)),
                 "posts_with_comments": int(cc["post_id"].nunique()), "brands": int(p["brand"].nunique()),
                 "platforms": int(p["platform"].nunique()), "campaigns": int(p["campaign"].nunique()),
                 "date_min": str(published.min())[:10] if len(p) else None,
                 "date_max": str(published.max())[:10] if len(p) else None,
                 "clusters": int(sum(1 for c in clusters if c["cluster_id"] != -1)),
                 "noise_share": clean(next((c["filtered_share"] for c in clusters if c["cluster_id"] == -1), 0.0)),
                 "anomaly_flags": int(len(fl)), "posts_flagged": int(fl["post_id"].nunique()),
                 "recommendations": int(len(f.recommendations))},
        "coverage": coverage(p), "engagement_by_platform": by_platform, "content": content,
        "top_clusters": top_clusters, "anomalies": frame_records(top_flags.drop(columns=["abs"])),
        "anomaly_counts": fl.groupby(["kind", "direction"]).size().reset_index(name="n").to_dict(orient="records"),
        "recommendations": recs, "language_mix": cc["language_type"].value_counts().to_dict(),
    }


@app.get(f"{V1}/analytics/content")
def analytics_content(dataset_id: str | None = None, filters: Filters = Depends(filters_dep)):
    f = load_frames(dataset_id)
    p = filtered_posts(f, filters)
    return {"meta": meta(f, len(p), filters, assumptions=[f"Mature = at least {MATURE_DAYS} days old at snapshot.",
                                                         "Associational, not causal."]),
            "formulas": FORMULAS, "coverage": coverage(p), **clean(content_analysis(p))}


@app.get(f"{V1}/analytics/campaigns")
def analytics_campaigns(dataset_id: str | None = None, filters: Filters = Depends(filters_dep)):
    f = load_frames(dataset_id)
    p = filtered_posts(f, filters)
    cc = _cc_filtered(f, p)
    res = campaign_analysis(p, cc[cc["need"].notna()])
    res["campaign_calendar"] = frame_records(f.campaigns, ["campaign_id", "name", "campaign_type", "start_date", "end_date",
                                                           "campaign_source"])
    return {"meta": meta(f, len(p), filters, f.selected_run), **clean(res)}


# ---------------------------------------------------------------- audience (Q2/Q4)
def _cc_filtered(f, posts_subset: pd.DataFrame) -> pd.DataFrame:
    cc = f.comments_clustered
    return cc[cc["post_id"].isin(set(posts_subset["post_id"]))]


def _cluster_rows(f, cc: pd.DataFrame) -> list[dict]:
    counts = cc["cluster_id"].value_counts()
    clustered = int(cc.loc[cc["cluster_id"] != -1].shape[0])
    rows = []
    for p in f.profiles.to_dict(orient="records"):
        n = int(counts.get(p["cluster_id"], 0))
        rows.append(clean({
            "cluster_id": p["cluster_id"], "label": p["label"], "need_category": p["need_category"],
            "need_label": NEED_LABELS.get(p["need_category"], p["need_category"]), "label_source": p["label_source"],
            "label_agreement": p["label_agreement"], "size": p["size"], "share": p["share"], "filtered_size": n,
            "filtered_share": (n / clustered if clustered and p["cluster_id"] != -1 else n / max(len(cc), 1)),
            "cohesion": p["cohesion"], "top_terms": loads(p["top_terms_json"], []),
            "language_mix": loads(p["language_mix_json"], {}), "need_mix": loads(p["need_mix_json"], {}),
            "exemplars": loads(p["exemplars_json"], []), "date_min": p["date_min"], "date_max": p["date_max"],
            "explanation": p["explanation"]}))
    return sorted(rows, key=lambda r: (r["cluster_id"] == -1, -r["filtered_size"]))


@app.get(f"{V1}/audience/clusters")
def clusters(dataset_id: str | None = None, filters: Filters = Depends(filters_dep)):
    f = load_frames(dataset_id)
    p = filtered_posts(f, filters)
    cc = _cc_filtered(f, p)
    rows = _cluster_rows(f, cc)
    lang = (cc.groupby(["cluster_id", "language_type"]).size().reset_index(name="n").to_dict(orient="records"))
    plat = (cc.groupby(["cluster_id", "platform"]).size().reset_index(name="n").to_dict(orient="records"))
    sel = f.selected_run or {}
    run_metrics = loads(sel.get("metrics_json"), {})
    return {"meta": meta(f, int(len(cc)), filters, sel, assumptions=[
                "Clusters were discovered without labels; names were attached afterwards by majority reference label.",
                "Shares use clustered (non-noise) comments as the denominator unless stated."]),
            "run": clean({"run_id": sel.get("run_id"), "embedding": sel.get("embedding"),
                          "embedding_model": sel.get("embedding_model"), "algorithm": sel.get("algorithm"),
                          "params": loads(sel.get("params_json"), {}), "n_comments": sel.get("n_comments"),
                          "n_clusters": sel.get("n_clusters"), "noise_rate": sel.get("noise_rate"),
                          "quality": {k: run_metrics.get(k) for k in ("silhouette_cosine", "davies_bouldin",
                                                                      "calinski_harabasz", "stability_ari", "size_entropy",
                                                                      "min_cluster_share", "max_cluster_share")},
                          "model_version": sel.get("model_version"), "created_at": sel.get("created_at")}),
            "comments_in_view": int(len(cc)), "clusters": rows, "language_by_cluster": clean(lang),
            "platform_by_cluster": clean(plat),
            "needs_by_campaign": clean(needs_by(cc[cc["need"].notna()], "campaign")),
            "needs_by_platform": clean(needs_by(cc[cc["need"].notna()], "platform"))}


@app.get(f"{V1}/audience/clusters/{{cluster_id}}")
def cluster_detail(cluster_id: int, dataset_id: str | None = None, filters: Filters = Depends(filters_dep),
                   page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                   language: str | None = None):
    f = load_frames(dataset_id)
    p = filtered_posts(f, filters)
    cc = _cc_filtered(f, p)
    prof = next((r for r in _cluster_rows(f, cc) if r["cluster_id"] == cluster_id), None)
    if prof is None:
        raise HTTPException(404, f"Cluster {cluster_id} not found in the selected run.")
    members = cc[cc["cluster_id"] == cluster_id]
    breakdowns = {}
    for dim in ("platform", "campaign", "brand", "content_type", "language_type"):
        overall = cc[dim].value_counts(normalize=True)
        inside = members[dim].value_counts()
        breakdowns[dim] = [{"value": k, "label": CONTENT_TYPE_LABELS.get(k, LANGUAGE_LABELS.get(k, k)), "n": int(v),
                            "share": round(v / max(len(members), 1), 4),
                            "lift": round((v / max(len(members), 1)) / overall[k], 3) if overall.get(k) else None}
                           for k, v in inside.items()]
    month = pd.to_datetime(members["published_at"], utc=True, errors="coerce").dt.strftime("%Y-%m")
    trend = month.value_counts().sort_index().to_dict()
    with_cluster = set(members["post_id"])
    commented = p[p["post_id"].isin(set(cc["post_id"])) & p["mature"]]
    ctx = {"posts_with_cluster_comments": len(with_cluster),
           "median_attention_index_posts_with_cluster": clean(commented[commented["post_id"].isin(with_cluster)]
                                                              ["attention_index"].median()),
           "median_attention_index_all_commented_posts": clean(commented["attention_index"].median())}
    sample = members.sort_values("distance", na_position="last")
    if language:
        sample = sample[sample["language_type"] == language]
    chunk, pg = paginate(sample, page, page_size)
    show = f.meta["text_permission"] != "withheld"
    rows = frame_records(chunk, ["comment_id", "post_id", "comment_text", "language_type", "topic", "sentiment",
                                 "purchase_intent", "distance", "platform", "campaign", "brand"])
    if not show:
        for r in rows:
            r["comment_text"] = None
    need = prof["need_category"]
    recs = [_rec(r) for r in f.recommendations.to_dict(orient="records")
            if r["audience_need"] == need or f'"id": {cluster_id},' in (r["linked_evidence_json"] or "")
            or f'"id": {cluster_id}}}' in (r["linked_evidence_json"] or "")]
    return {"meta": meta(f, len(members), filters, f.selected_run), "cluster": prof, "breakdowns": clean(breakdowns),
            "monthly": trend, "engagement_context": ctx, "comments": rows, "page": pg,
            "comments_note": None if show else "Comment text is withheld for this dataset (derived labels only).",
            "recommendations": recs}


@app.get(f"{V1}/audience/evaluation")
def evaluation(dataset_id: str | None = None):
    f = load_frames(dataset_id)
    return {"meta": meta(f, f.meta["comment_count"], run=f.selected_run), "evaluation": clean(f.evaluation),
            "runs": frame_records(f.cluster_runs.drop(columns=["metrics_json"]).assign(
                metrics=[loads(m, {}) for m in f.cluster_runs["metrics_json"]]))}


# ---------------------------------------------------------------- comments
@app.get(f"{V1}/comments")
def comments(dataset_id: str | None = None, filters: Filters = Depends(filters_dep), cluster_id: int | None = None,
             language: str | None = None, topic: str | None = None, intent: str | None = None,
             sentiment: str | None = None, q: str | None = Query(None, max_length=80),
             page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=200)):
    f = load_frames(dataset_id)
    p = filtered_posts(f, filters)
    cc = _cc_filtered(f, p)
    for col, val in (("cluster_id", cluster_id), ("language_type", language), ("topic", topic),
                     ("purchase_intent", intent), ("sentiment", sentiment)):
        if val is not None:
            cc = cc[cc[col] == val]
    withheld = f.meta["text_permission"] == "withheld"
    if q and not withheld:
        cc = cc[cc["comment_text"].fillna("").str.contains(q, case=False, regex=False)]
    summary = {"languages": cc["language_type"].value_counts().to_dict(), "topics": cc["topic"].value_counts().to_dict(),
               "intent": cc["purchase_intent"].value_counts().to_dict(),
               "sentiment": cc["sentiment"].value_counts().to_dict()}
    chunk, pg = paginate(cc.sort_values("comment_id"), page, page_size)
    rows = frame_records(chunk, ["comment_id", "post_id", "comment_text", "language_type", "topic", "topic_confidence",
                                 "sentiment", "purchase_intent", "cluster_id", "cluster_label", "need", "published_at",
                                 "platform", "brand", "campaign", "content_type"])
    if withheld:
        for r in rows:
            r["comment_text"] = None
    return {"meta": meta(f, len(cc), filters, f.selected_run, assumptions=[
                "Topic is a rule-based reference label (interpretation aid); cluster is the discovered group.",
                "Purchase intent 'possible_inquiry' is a question about buying, not a confirmed purchase.",
                "Sentiment is a lexicon heuristic, shown only as a supporting signal."]),
            "permission": {"text_permission": f.meta["text_permission"], "text_visible": not withheld,
                           "note": ("Synthetic illustrative comments (not real people)." if f.meta["mode"] == "synthetic"
                                    else "Comment text withheld: derived labels only." if withheld else
                                    "Imported comments shown as attested by the uploader.")},
            "summary": summary, "page": pg, "rows": rows}


# ---------------------------------------------------------------- anomalies (Q3)
@app.get(f"{V1}/anomalies")
def anomalies(dataset_id: str | None = None, filters: Filters = Depends(filters_dep), kind: str | None = None,
              direction: str | None = Query(None, pattern="^(positive|negative)$"),
              severity: str | None = Query(None, pattern="^(high|medium)$"),
              page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200)):
    f = load_frames(dataset_id)
    p = filtered_posts(f, filters)
    fl = f.flags[f.flags["post_id"].isin(set(p["post_id"]))]
    for col, val in (("kind", kind), ("direction", direction), ("severity", severity)):
        if val:
            fl = fl[fl[col] == val]
    fl = fl.merge(p[["post_id", "brand", "platform", "content_type", "campaign", "published_at", "likes",
                     "comments_count", "shares", "views", "days_since_post", "source_url"]], on="post_id", how="left")
    fl = fl.assign(abs_score=fl["score"].abs()).sort_values(["severity", "abs_score"], ascending=[True, False])
    chunk, pg = paginate(fl.drop(columns=["abs_score"]), page, page_size)
    scores = f.scores[f.scores["post_id"].isin(set(p["post_id"]))]
    z = scores["robust_z"].dropna().clip(-8, 8)
    hist, edges = np.histogram(z, bins=32, range=(-8, 8)) if len(z) else (np.array([]), np.array([]))
    run = f.anomaly_run or {}
    return {"meta": meta(f, int(len(scores)), filters, run, model_version=run.get("model_version"), assumptions=[
                "Flags are statistical outliers vs comparable posts — not accusations of fraud or bot activity."]),
            "run": clean({"run_id": run.get("run_id"), "method": run.get("method"), "params": loads(run.get("params_json"), {}),
                          "metrics": loads(run.get("metrics_json"), {})}),
            "summary": {"flags": int(len(fl)), "posts": int(fl["post_id"].nunique()),
                        "by_kind": fl["kind"].value_counts().to_dict(), "by_direction": fl["direction"].value_counts().to_dict(),
                        "by_severity": fl["severity"].value_counts().to_dict(), "posts_scored": int(len(scores))},
            "z_histogram": [{"from": round(float(edges[i]), 2), "to": round(float(edges[i + 1]), 2), "n": int(hist[i])}
                            for i in range(len(hist))],
            "page": pg, "rows": frame_records(chunk)}


@app.get(f"{V1}/anomalies/{{flag_id}}")
def anomaly_detail(flag_id: str, dataset_id: str | None = None):
    f = load_frames(dataset_id)
    fl = f.flags[f.flags["flag_id"] == flag_id]
    if fl.empty:
        raise HTTPException(404, f"Anomaly flag '{flag_id}' not found.")
    flag = frame_records(fl)[0]
    post = f.posts[f.posts["post_id"] == flag["post_id"]]
    cohort = f.scores[f.scores["cohort_key"] == flag["cohort_key"]]
    vals = cohort["value"].astype(float)
    qs = {f"p{q}": clean(vals.quantile(q / 100)) for q in (5, 25, 50, 75, 95)} if len(vals) else {}
    logv = np.log(vals.clip(lower=1e-6)) if len(vals) else pd.Series(dtype=float)
    hist, edges = np.histogram(logv, bins=20) if len(vals) else (np.array([]), np.array([]))
    cc = f.comments_clustered
    post_mix = cc[cc["post_id"] == flag["post_id"]]["need"].value_counts().to_dict()
    cohort_mix = cc[cc["post_id"].isin(set(cohort["post_id"]))]["need"].value_counts(normalize=True).round(4).to_dict()
    return {"meta": meta(f, len(cohort), run=f.anomaly_run), "flag": flag, "post": frame_records(post)[0] if len(post) else None,
            "all_flags_for_post": frame_records(f.flags[f.flags["post_id"] == flag["post_id"]]),
            "cohort": {"key": flag["cohort_key"], "size": int(len(cohort)), "quantiles": qs,
                       "histogram_log": [{"from": float(np.exp(edges[i])), "to": float(np.exp(edges[i + 1])), "n": int(hist[i])}
                                         for i in range(len(hist))]},
            "need_mix_post": post_mix, "need_mix_cohort": cohort_mix}


# ---------------------------------------------------------------- recommendations (Q5)
def _rec(r: dict) -> dict:
    return clean({"recommendation_id": r["recommendation_id"], "title": r["title"], "action_type": r["action_type"],
                  "what_to_do": r["what_to_do"], "why_it_matters": r["why_it_matters"], "audience_need": r["audience_need"],
                  "audience_need_label": NEED_LABELS.get(r["audience_need"] or "", None),
                  "where": loads(r["where_json"], {}), "linked_evidence": loads(r["linked_evidence_json"], []),
                  "priority": int(r["priority"]), "evidence_strength": r["evidence_strength"],
                  "sample_size": int(r["sample_size"]), "metrics": loads(r["metrics_json"], {}),
                  "limitations": loads(r["limitations_json"], []), "test_plan": r["test_plan"],
                  "generated_at": r["generated_at"]})


@app.get(f"{V1}/recommendations")
def recommendations(dataset_id: str | None = None, action_type: str | None = None, priority: int | None = Query(None, ge=1, le=3),
                    strength: str | None = None, need: str | None = None):
    f = load_frames(dataset_id)
    rows = [_rec(r) for r in f.recommendations.to_dict(orient="records")]
    if action_type:
        rows = [r for r in rows if r["action_type"] == action_type]
    if priority:
        rows = [r for r in rows if r["priority"] == priority]
    if strength:
        rows = [r for r in rows if r["evidence_strength"] == strength]
    if need:
        rows = [r for r in rows if r["audience_need"] == need]
    return {"meta": meta(f, len(rows), run=f.selected_run, assumptions=[
                "Cards are generated deterministically from linked evidence; no LLM is used.",
                "A card appears only when its evidence passes the gates listed in Methodology."]),
            "llm_wording_enabled": get_settings().llm_enabled, "recommendations": rows,
            "counts": {"by_action": pd.Series([r["action_type"] for r in rows]).value_counts().to_dict() if rows else {},
                       "by_priority": pd.Series([r["priority"] for r in rows]).value_counts().to_dict() if rows else {}}}


@app.get(f"{V1}/recommendations/{{recommendation_id}}")
def recommendation_detail(recommendation_id: str, dataset_id: str | None = None):
    f = load_frames(dataset_id)
    rec = f.recommendations[f.recommendations["recommendation_id"] == recommendation_id]
    if rec.empty:
        raise HTTPException(404, f"Recommendation '{recommendation_id}' not found.")
    return {"meta": meta(f, None, run=f.selected_run), "recommendation": _rec(rec.iloc[0].to_dict())}


# ---------------------------------------------------------------- data, imports, reports, methodology
@app.get(f"{V1}/data/quality")
def data_quality(dataset_id: str | None = None):
    f = load_frames(dataset_id)
    return {"meta": meta(f, f.meta["post_count"]), **clean(quality_report(f))}


@app.get(f"{V1}/imports/templates/{{kind}}")
def import_template(kind: str):
    try:
        body = importer.template_csv(kind)
    except KeyError:
        raise HTTPException(404, "Template must be 'posts' or 'comments'.") from None
    return Response(body, media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{kind}_template.csv"'})


def _check_sizes(req: schemas.ImportPreviewRequest):
    limit = get_settings().max_upload_bytes
    for name, text in (("posts", req.posts_csv), ("comments", req.comments_csv)):
        if text and len(text.encode("utf-8")) > limit:
            raise HTTPException(413, f"The {name} CSV is larger than the {limit // 1024:,} KB limit.")


@app.post(f"{V1}/imports/preview")
def import_preview(req: schemas.ImportPreviewRequest):
    _check_sizes(req)
    if not req.posts_csv and not req.comments_csv:
        raise HTTPException(422, "Provide a posts CSV, a comments CSV, or both.")
    return clean(importer.preview(req.posts_csv, req.comments_csv, req.posts_mapping, req.comments_mapping))


@app.post(f"{V1}/imports/confirm")
def import_confirm(req: schemas.ImportConfirmRequest):
    _check_sizes(req)
    if not req.attestation.permission_confirmed:
        raise HTTPException(422, "Confirm that you are allowed to use and store this data.")
    from audienceiq.services.datasets import build_import

    result = build_import(req)
    return clean(result)


@app.get(f"{V1}/reports/export")
def report_export(dataset_id: str | None = None, filters: Filters = Depends(filters_dep),
                  format: str = Query("csv", pattern="^(csv|xlsx|pdf)$"), section: str = Query("summary")):
    if section not in export.SECTIONS:
        raise HTTPException(422, f"section must be one of {export.SECTIONS}")
    f = load_frames(dataset_id)
    p = filtered_posts(f, filters)
    stamp = datetime.now(UTC).strftime("%Y%m%d")
    base = f"audienceiq_{f.meta['dataset_id']}_{stamp}"
    if format == "csv":
        return Response(export.to_csv(f, section, p), media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": f'attachment; filename="{base}_{section}.csv"'})
    if format == "xlsx":
        return Response(export.to_xlsx(f, p), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        headers={"Content-Disposition": f'attachment; filename="{base}.xlsx"'})
    return Response(export.to_pdf(f, p, compare(p, "content_type", "attention_index")), media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{base}_summary.pdf"'})


@app.get(f"{V1}/methodology")
def methodology(dataset_id: str | None = None):
    f = load_frames(dataset_id)
    return {"meta": meta(f, f.meta["comment_count"], run=f.selected_run), **clean(methodology_payload(f))}


def expiry_for(snapshot: datetime) -> str:
    return (snapshot + timedelta(days=30)).isoformat(timespec="seconds")
