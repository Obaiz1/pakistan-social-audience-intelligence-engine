"""Q1 content & campaign analytics on enriched posts (analytics.engagement.add_engagement output).

Rules: only mature posts enter comparisons (immature counts are reported); groups with n < 20 are shown but not
tested; medians come with bootstrap 95% CIs; tests are Mann-Whitney vs all other posts with Cliff's δ and
Benjamini–Hochberg correction (Repo A statistics). Weighted engagement rate = Σ interactions / Σ views over posts that
report both (never an average of ratios). Everything is associational.
"""

import math

import numpy as np
import pandas as pd

from audienceiq.analytics.stats import MIN_N, compare_groups
from audienceiq.constants import CONTENT_TYPE_LABELS

METRIC_HELP = {
    "attention_index": "Interactions relative to the same brand's typical mature post on the same platform (1.00 = typical).",
    "er_views": "Interactions ÷ views, only where views are reported. Formula per platform in Methodology.",
    "er_index": "Engagement rate relative to the same brand × platform median engagement rate (1.00 = typical).",
    "interactions": "Likes + comments (+ shares where the platform reports them).",
}


def _clean(v):
    if v is None:
        return None
    if isinstance(v, (float, np.floating)):
        return None if math.isnan(v) or math.isinf(v) else round(float(v), 6)
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    return v


def records(df: pd.DataFrame) -> list[dict]:
    return [{k: _clean(v) for k, v in row.items()} for row in df.to_dict(orient="records")]


def weighted_er(df: pd.DataFrame) -> float | None:
    both = df[df["views"].notna() & df["interactions"].notna() & (df["views"].astype(float) > 0)]
    if both.empty:
        return None
    return float(both["interactions"].astype(float).sum() / both["views"].astype(float).sum())


def compare(df: pd.DataFrame, by: str, metric: str) -> dict:
    mature = df[df["mature"]]
    table = compare_groups(mature, by, metric) if mature[metric].notna().sum() else pd.DataFrame()
    rows = []
    if not table.empty:
        for r in records(table):
            g = mature[mature[by] == r["group"]]
            r.update({"posts_total": int((df[by] == r["group"]).sum()), "posts_mature": int(len(g)),
                      "weighted_er": _clean(weighted_er(g)),
                      "label": CONTENT_TYPE_LABELS.get(r["group"], r["group"]) if by == "content_type" else r["group"]})
            rows.append(r)
    return {"dimension": by, "metric": metric, "metric_help": METRIC_HELP.get(metric, ""), "min_n": MIN_N,
            "kruskal_p": _clean(table.attrs.get("kruskal_p")) if not table.empty else None,
            "posts_compared": int(mature[metric].notna().sum()), "posts_excluded_immature": int((~df["mature"]).sum()),
            "rows": rows}


def distribution(df: pd.DataFrame, by: str, metric: str) -> list[dict]:
    out = []
    mature = df[df["mature"] & df[metric].notna()]
    for g, sub in mature.groupby(by):
        v = sub[metric].astype(float)
        out.append({"group": g, "label": CONTENT_TYPE_LABELS.get(g, g) if by == "content_type" else g, "n": int(len(v)),
                    **{f"p{q}": _clean(v.quantile(q / 100)) for q in (10, 25, 50, 75, 90)}})
    return sorted(out, key=lambda r: -(r["p50"] or 0))


def platform_matrix(df: pd.DataFrame) -> list[dict]:
    rows = []
    mature = df[df["mature"]]
    for (plat, ct), g in mature.groupby(["platform", "content_type"]):
        rows.append({"platform": plat, "content_type": ct, "label": CONTENT_TYPE_LABELS.get(ct, ct), "n": int(len(g)),
                     "sufficient": bool(len(g) >= MIN_N),
                     "median_attention_index": _clean(g["attention_index"].median()),
                     "median_er_views": _clean(g["er_views"].median()), "weighted_er": _clean(weighted_er(g)),
                     "views_reported_share": round(float(g["views"].notna().mean()), 4),
                     "shares_reported_share": round(float(g["shares"].notna().mean()), 4)})
    return rows


def top_bottom(df: pd.DataFrame, metric: str = "attention_index", n: int = 5) -> dict:
    mature = df[df["mature"] & df[metric].notna()].sort_values(metric)
    cols = ["post_id", "brand", "platform", "content_type", "campaign", "likes", "comments_count", "shares", "views",
            "er_views", "attention_index", "days_since_post", "source_url"]
    return {"metric": metric, "top": records(mature.tail(n)[cols].iloc[::-1]), "bottom": records(mature.head(n)[cols])}


def content_analysis(df: pd.DataFrame) -> dict:
    return {
        "by_content_type": compare(df, "content_type", "attention_index"),
        "by_content_type_er": compare(df[df["er_views"].notna()], "content_type", "er_index"),
        "by_platform": compare(df, "platform", "er_views"),
        "distribution": distribution(df, "content_type", "attention_index"),
        "platform_matrix": platform_matrix(df),
        "top_bottom": top_bottom(df),
        "notes": [
            "Platforms report different metrics; engagement rates are not directly comparable across platforms.",
            "Attention index compares each post with its own brand × platform baseline, so content types can be compared.",
            "Product photos and graphic sale posts on Instagram/Facebook report no views, so they have no view-based ER.",
        ],
    }


def campaign_analysis(df: pd.DataFrame, comment_needs: pd.DataFrame | None = None) -> dict:
    comp = compare(df, "campaign", "attention_index")
    meta = []
    for camp, g in df.groupby("campaign"):
        immature = float((~g["mature"]).mean())
        meta.append({"campaign": camp, "posts": int(len(g)), "posts_mature": int(g["mature"].sum()),
                     "immature_share": round(immature, 4), "maturity_warning": immature > 0.5,
                     "date_min": str(g["published_at"].min())[:10], "date_max": str(g["published_at"].max())[:10],
                     "platforms": g["platform"].value_counts().to_dict(),
                     "content_types": g["content_type"].value_counts().to_dict(),
                     "weighted_er": _clean(weighted_er(g[g["mature"]])),
                     "median_attention_index": _clean(g.loc[g["mature"], "attention_index"].median())})
    needs = needs_by(comment_needs, "campaign") if comment_needs is not None else []
    return {"comparison": comp, "campaigns": sorted(meta, key=lambda r: -r["posts"]), "needs_by_campaign": needs}


def needs_by(cn: pd.DataFrame, dim: str, min_comments: int = 30) -> list[dict]:
    """Share of each discovered need within a dimension value, with lift vs the overall share.

    cn: one row per clustered comment with columns `need`, `cluster_label`, and the post dimension (campaign, ...).
    """
    if cn is None or cn.empty:
        return []
    c = cn[~cn["need"].isin(["noise"])]
    overall = c["need"].value_counts(normalize=True)
    rows = []
    for val, g in c.groupby(dim):
        if len(g) < min_comments:
            rows.append({dim: val, "comments": int(len(g)), "sufficient": False, "needs": []})
            continue
        shares = g["need"].value_counts(normalize=True)
        rows.append({dim: val, "comments": int(len(g)), "sufficient": True,
                     "needs": [{"need": k, "share": round(float(v), 4), "lift": round(float(v / overall[k]), 3)}
                               for k, v in shares.items()]})
    return rows
