"""Post-level anomaly detection against COMPARABLE posts (Q3). Statistical outliers only — never fraud claims.

Method (docs/ANOMALY_METHOD.md, ADR-009):
1. Scored population: mature posts (days_since_post >= 7) with a non-null primary metric.
   Primary metric = er_views (interactions / views) when views are reported, otherwise interactions; the metric kind is
   part of the cohort key so view-based and count-based posts are never compared with each other.
2. Peer cohort: the most specific of brand × platform × content type → platform × content type → platform that has
   at least MIN_COHORT scored posts. Posts with no qualifying cohort are not scored (reported as such).
3. Robust z = (log value − cohort median of log values) / (1.4826 × MAD). |z| >= Z_THRESHOLD (3.5, Iglewicz & Hoaglin)
   flags an engagement anomaly; the sign gives the direction (positive = far above peers).
4. Comment pattern: robust z of log(comments / likes) in the same cohort, only for posts with >= MIN_COMMENTS comments.
5. Need-mix shift: for posts with >= MIN_MIX_COMMENTS clustered comments, an exact binomial test of the most
   over-represented discovered need vs the pooled share among cohort posts (Bonferroni within post, Benjamini–Hochberg
   across posts); flagged when adjusted p < MIX_ALPHA and the share is >= 2× expected and >= 40%.
6. Isolation Forest (seed 42) on the per-post standardized features is a secondary multivariate score; posts that only
   Isolation Forest finds (top IFOREST_TOP share) are listed as lower-confidence "multivariate" flags.
"""

import json
from datetime import UTC, datetime

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import IsolationForest

from audienceiq.analytics.stats import benjamini_hochberg
from audienceiq.constants import CONTENT_TYPE_LABELS, NEED_LABELS

MODEL_VERSION = "anomaly-v1.0"
MIN_COHORT = 20
Z_THRESHOLD = 3.5
HIGH_Z = 5.0
MIN_COMMENTS = 20
MIN_MIX_COMMENTS = 8
MIX_ALPHA = 0.01
IFOREST_TOP = 0.01
SEED = 42
CAVEAT = ("Statistical outlier relative to comparable posts — not evidence of fraud, bots or paid activity. Possible "
          "explanations include paid promotion, an influencer repost, a giveaway, a data-entry error or genuinely "
          "exceptional content. Investigate before repeating or dropping the approach.")
LEVELS = [("brand_platform_type", ["brand", "platform", "content_type"]),
          ("platform_type", ["platform", "content_type"]),
          ("platform", ["platform"])]


def _robust_z(values: pd.Series) -> pd.Series:
    med = values.median()
    mad = (values - med).abs().median() * 1.4826
    if not mad or np.isnan(mad):
        mad = (values - values.mean()).abs().mean() * 1.2533
    if not mad or np.isnan(mad):
        return pd.Series(np.nan, index=values.index)
    return (values - med) / mad


def _fmt(metric: str, v: float | None) -> str:
    if v is None or pd.isna(v):
        return "n/a"
    return f"{v * 100:.2f}%" if metric == "er_views" else f"{v:,.0f}" if metric == "interactions" else f"{v:.3f}"


def assign_cohorts(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["metric"] = np.where(df["er_views"].notna(), "er_views", "interactions")
    df["value"] = np.where(df["er_views"].notna(), df["er_views"].astype(float),
                           df["interactions"].astype(float))
    scored = df["mature"].astype(bool) & pd.notna(df["value"]) & (df["value"] >= 0)
    df["cohort_key"], df["cohort_level"], df["cohort_size"] = None, None, 0
    remaining = scored.copy()
    for level, cols in LEVELS:
        keys = df[cols + ["metric"]].astype(str).agg(" · ".join, axis=1)
        sizes = keys[scored].value_counts()
        ok = remaining & keys.map(sizes).fillna(0).ge(MIN_COHORT)
        df.loc[ok, "cohort_key"] = keys[ok]
        df.loc[ok, "cohort_level"] = level
        df.loc[ok, "cohort_size"] = keys[ok].map(sizes).astype(int)
        remaining &= ~ok
    df["scored"] = df["cohort_key"].notna()
    return df


def detect(posts: pd.DataFrame, comments: pd.DataFrame | None = None, dataset_id: str = "",
           run_id: str | None = None) -> dict:
    """posts: output of analytics.engagement.add_engagement. comments (optional): post_id + need (discovered cluster need)."""
    run_id = run_id or f"anom-{dataset_id}-{MODEL_VERSION}"
    df = assign_cohorts(posts)
    sc = df[df["scored"]].copy()
    sc["log_value"] = np.log(sc["value"].astype(float) + np.where(sc["metric"] == "er_views", 1e-5, 1.0))
    sc["robust_z"] = sc.groupby("cohort_key")["log_value"].transform(_robust_z)
    ratio = sc["comment_ratio"].astype(float)
    sc["log_ratio"] = np.log(ratio.where(ratio > 0))
    sc["comment_ratio_z"] = sc.groupby("cohort_key")["log_ratio"].transform(_robust_z)
    sc.loc[sc["comments_count"].astype(float) < MIN_COMMENTS, "comment_ratio_z"] = np.nan

    cohort_stats = sc.groupby("cohort_key")["value"].agg(
        baseline_median="median", expected_low=lambda s: s.quantile(0.05), expected_high=lambda s: s.quantile(0.95))
    ratio_stats = sc.groupby("cohort_key")["comment_ratio"].agg(
        ratio_median=lambda s: s.astype(float).median(),
        ratio_low=lambda s: s.astype(float).quantile(0.05), ratio_high=lambda s: s.astype(float).quantile(0.95))
    sc = sc.join(cohort_stats, on="cohort_key").join(ratio_stats, on="cohort_key")

    mix = _need_mix_tests(sc, comments)
    sc = sc.join(mix, on="post_id") if not mix.empty else sc.assign(mix_padj=np.nan)

    feats = pd.DataFrame({"z": sc["robust_z"].fillna(0), "rz": sc["comment_ratio_z"].fillna(0),
                          "mix": sc.get("mix_excess", pd.Series(0, index=sc.index)).fillna(0)})
    if len(sc) >= 50:
        forest = IsolationForest(n_estimators=200, contamination="auto", random_state=SEED).fit(feats)
        sc["iforest_score"] = -forest.score_samples(feats)
        cutoff = sc["iforest_score"].quantile(1 - IFOREST_TOP)
    else:
        sc["iforest_score"], cutoff = np.nan, np.inf

    flags = []
    for r in sc.itertuples(index=False):
        base = dict(post_id=r.post_id, cohort_key=r.cohort_key, cohort_level=r.cohort_level,
                    cohort_size=int(r.cohort_size), iforest_score=_f(r.iforest_score))
        who = f"{r.platform} · {CONTENT_TYPE_LABELS.get(r.content_type, r.content_type)}"
        if pd.notna(r.robust_z) and abs(r.robust_z) >= Z_THRESHOLD:
            direction = "positive" if r.robust_z > 0 else "negative"
            label = "Engagement rate" if r.metric == "er_views" else "Interactions"
            flags.append(base | dict(
                kind="engagement", metric=r.metric, value=_f(r.value), baseline_median=_f(r.baseline_median),
                expected_low=_f(r.expected_low), expected_high=_f(r.expected_high), score=round(float(r.robust_z), 3),
                direction=direction, severity="high" if abs(r.robust_z) >= HIGH_Z else "medium",
                reason=(f"{label} {_fmt(r.metric, r.value)} vs cohort median {_fmt(r.metric, r.baseline_median)} "
                        f"(typical range P5–P95 {_fmt(r.metric, r.expected_low)}–{_fmt(r.metric, r.expected_high)}) among "
                        f"{int(r.cohort_size)} mature {_cohort_words(r)} posts; robust z = {r.robust_z:+.1f}. "
                        f"{'Far above' if direction == 'positive' else 'Far below'} comparable {who} posts.")))
        if pd.notna(r.comment_ratio_z) and abs(r.comment_ratio_z) >= Z_THRESHOLD:
            direction = "positive" if r.comment_ratio_z > 0 else "negative"
            flags.append(base | dict(
                kind="comment_pattern", metric="comments_per_like", value=_f(r.comment_ratio),
                baseline_median=_f(r.ratio_median), expected_low=_f(r.ratio_low), expected_high=_f(r.ratio_high),
                score=round(float(r.comment_ratio_z), 3), direction=direction,
                severity="high" if abs(r.comment_ratio_z) >= HIGH_Z else "medium",
                reason=(f"{int(r.comments_count):,} comments for {int(r.likes):,} likes = {r.comment_ratio:.3f} comments per "
                        f"like vs cohort median {r.ratio_median:.3f} (P5–P95 {r.ratio_low:.3f}–{r.ratio_high:.3f}) among "
                        f"{int(r.cohort_size)} comparable posts; robust z = {r.comment_ratio_z:+.1f}. "
                        + ("Unusually comment-heavy: check for questions, complaints or a giveaway."
                           if direction == "positive" else "Unusually few comments for its likes."))))
        if pd.notna(getattr(r, "mix_padj", np.nan)) and r.mix_padj < MIX_ALPHA:
            need = NEED_LABELS.get(r.mix_need, r.mix_need)
            flags.append(base | dict(
                kind="need_mix", metric=f"share:{r.mix_need}", value=_f(r.mix_share), baseline_median=_f(r.mix_expected),
                expected_low=None, expected_high=None, score=round(float(-np.log10(max(r.mix_padj, 1e-300))), 3),
                direction="positive", severity="high" if r.mix_padj < 0.001 else "medium",
                reason=(f"{r.mix_k} of {r.mix_n} clustered comments ({r.mix_share:.0%}) fall in the discovered "
                        f"'{need}' need vs {r.mix_expected:.0%} across comparable posts (exact binomial test, "
                        f"Benjamini–Hochberg adjusted p = {r.mix_padj:.1e}).")))
    flagged_posts = {f["post_id"] for f in flags}
    for r in sc.itertuples(index=False):
        if r.post_id not in flagged_posts and pd.notna(r.iforest_score) and r.iforest_score >= cutoff:
            flags.append(dict(
                post_id=r.post_id, cohort_key=r.cohort_key, cohort_level=r.cohort_level, cohort_size=int(r.cohort_size),
                iforest_score=_f(r.iforest_score), kind="multivariate", metric="isolation_forest",
                value=_f(r.iforest_score), baseline_median=_f(sc["iforest_score"].median()), expected_low=None,
                expected_high=_f(cutoff), score=round(float(r.iforest_score), 3),
                direction="positive" if (r.robust_z or 0) >= 0 else "negative", severity="medium",
                reason=(f"Isolation Forest places this post in the most isolated {IFOREST_TOP:.0%} of scored posts "
                        f"(score {r.iforest_score:.3f} vs median {sc['iforest_score'].median():.3f}) from the combination "
                        f"of engagement z = {(r.robust_z or 0):+.1f}, comment-ratio z = "
                        f"{(r.comment_ratio_z if pd.notna(r.comment_ratio_z) else 0):+.1f} and need mix; no single rule "
                        "crossed its threshold, so treat as lower confidence.")))
    for i, f in enumerate(sorted(flags, key=lambda f: (f["post_id"], f["kind"]))):
        f["flag_id"] = f"{run_id}-F{i + 1:04d}"
        f["caveat"] = CAVEAT
        f["run_id"], f["dataset_id"] = run_id, dataset_id

    sensitivity = {f"|z|>={t}": int((sc["robust_z"].abs() >= t).sum()) for t in (3.0, 3.5, 4.0, 5.0)}
    rule_flagged = {f["post_id"] for f in flags if f["kind"] != "multivariate"}
    top5 = set(sc.loc[sc["iforest_score"] >= sc["iforest_score"].quantile(0.95), "post_id"]) if len(sc) >= 50 else set()
    metrics = {
        "posts_total": int(len(df)), "posts_mature": int(df["mature"].sum()), "posts_scored": int(len(sc)),
        "posts_unscored_small_cohort": int((df["mature"] & ~df["scored"] & df["value"].notna()).sum()),
        "posts_immature": int((~df["mature"]).sum()), "flags": len(flags), "posts_flagged": len({f['post_id'] for f in flags}),
        "by_kind": pd.Series([f["kind"] for f in flags]).value_counts().to_dict() if flags else {},
        "by_direction": pd.Series([f["direction"] for f in flags]).value_counts().to_dict() if flags else {},
        "cohort_levels": sc["cohort_level"].value_counts().to_dict(), "sensitivity_engagement": sensitivity,
        "iforest_agreement_top5pct": round(len(rule_flagged & top5) / len(rule_flagged), 3) if rule_flagged and top5 else None,
    }
    params = {"min_cohort": MIN_COHORT, "z_threshold": Z_THRESHOLD, "high_z": HIGH_Z, "min_comments": MIN_COMMENTS,
              "min_mix_comments": MIN_MIX_COMMENTS, "mix_alpha": MIX_ALPHA, "iforest_top": IFOREST_TOP, "seed": SEED,
              "mature_days": 7, "levels": [lv for lv, _ in LEVELS]}
    run = {"run_id": run_id, "dataset_id": dataset_id, "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
           "method": "peer-cohort robust z (median/MAD) + binomial need-mix test + Isolation Forest (secondary)",
           "params_json": json.dumps(params), "n_posts_scored": int(len(sc)), "n_flagged": metrics["posts_flagged"],
           "metrics_json": json.dumps(metrics), "model_version": MODEL_VERSION}
    scores = pd.DataFrame({
        "run_id": run_id, "dataset_id": dataset_id, "post_id": sc["post_id"], "cohort_key": sc["cohort_key"],
        "cohort_level": sc["cohort_level"], "cohort_size": sc["cohort_size"].astype(int), "metric": sc["metric"],
        "value": sc["value"].astype(float), "robust_z": sc["robust_z"].astype(float).round(4),
        "comment_ratio_z": sc["comment_ratio_z"].astype(float).round(4),
        "iforest_score": sc["iforest_score"].astype(float).round(4),
        "flagged": sc["post_id"].isin(flagged_posts | {f["post_id"] for f in flags}).astype(int)})
    return {"run": run, "flags": pd.DataFrame(flags), "scores": scores, "metrics": metrics}


def _cohort_words(r) -> str:
    if r.cohort_level == "brand_platform_type":
        return f"{r.brand} {r.platform} {CONTENT_TYPE_LABELS.get(r.content_type, r.content_type).lower()}"
    if r.cohort_level == "platform_type":
        return f"{r.platform} {CONTENT_TYPE_LABELS.get(r.content_type, r.content_type).lower()}"
    return f"{r.platform}"


def _f(v) -> float | None:
    return None if v is None or pd.isna(v) else round(float(v), 6)


def _need_mix_tests(sc: pd.DataFrame, comments: pd.DataFrame | None) -> pd.DataFrame:
    if comments is None or comments.empty or "need" not in comments:
        return pd.DataFrame()
    c = comments[comments["need"].notna() & ~comments["need"].isin(["noise", "mixed"])]
    c = c[c["post_id"].isin(sc["post_id"])]
    if c.empty:
        return pd.DataFrame()
    counts = c.groupby(["post_id", "need"]).size().unstack(fill_value=0)
    cohort_of = sc.set_index("post_id")["cohort_key"]
    counts["cohort"] = counts.index.map(cohort_of)
    pooled = counts.groupby("cohort").sum()
    rows = []
    needs = [col for col in counts.columns if col != "cohort"]
    for pid, row in counts.iterrows():
        n = int(row[needs].sum())
        if n < MIN_MIX_COMMENTS:
            continue
        tot = pooled.loc[row["cohort"], needs]
        expected = (tot / tot.sum()).astype(float)
        share = row[needs].astype(float) / n
        excess = (share - expected).idxmax()
        k, p0 = int(row[excess]), float(expected[excess])
        p = float(stats.binomtest(k, n, max(p0, 1e-6), alternative="greater").pvalue) * len(needs)
        ok = share[excess] >= 0.40 and share[excess] >= 2 * p0
        rows.append({"post_id": pid, "mix_need": excess, "mix_k": k, "mix_n": n, "mix_share": float(share[excess]),
                     "mix_expected": p0, "mix_p": min(p, 1.0) if ok else np.nan,
                     "mix_excess": float(share[excess] - p0)})
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out["mix_padj"] = benjamini_hochberg(out["mix_p"])
    return out.set_index("post_id")
