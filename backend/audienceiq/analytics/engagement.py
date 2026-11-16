"""Platform-aware engagement metrics. Missing values stay missing; zero is never used as a stand-in.

Metric definitions (also served by /api/v1/methodology):
- interactions  = likes + comments_count + shares for platforms whose data reports shares (Instagram, TikTok,
                  Facebook exports); likes + comments_count on YouTube (the API reports no shares). If a component
                  the platform formula needs is missing (e.g. hidden likes), interactions is null.
- er_views      = interactions / views, only when views > 0 is reported (reels/videos). Never computed for photos.
- attention_index = interactions / median interactions of MATURE posts of the same brand × platform
                  (1.00 = that brand's typical post on that platform). Removes brand-size and platform-scale effects,
                  so content types can be compared, including photos without view counts.
- er_index      = er_views / median er_views of mature view-bearing posts of the same brand × platform.
- comment_ratio = comments_count / likes (null when likes are missing or 0).
- mature        = days_since_post >= MATURE_DAYS; immature posts are excluded from baselines and comparisons
                  (they have not finished accumulating engagement) and the excluded count is always reported.

Adapted from Repo A src/processing/metrics.py (@957e3b6: null-propagating _ratio, within-brand relative ER).
"""

import pandas as pd

MATURE_DAYS = 7
SHARE_COVERAGE_MIN = 0.95
SHARES_REPORTED = {"Instagram": True, "TikTok": True, "Facebook": True, "YouTube": False, "Other": False}
FORMULAS = {
    "Instagram": "(likes + comments + shares) / views",
    "TikTok": "(likes + comments + shares) / views",
    "Facebook": "(likes + comments + shares) / views",
    "YouTube": "(likes + comments) / views — YouTube reports no share count",
    "Other": "(likes + comments) / views",
}


def _ratio(num: pd.Series, den: pd.Series) -> pd.Series:
    num, den = num.astype("Float64"), den.astype("Float64")
    return (num / den.where(den > 0)).astype("Float64")


def add_engagement(posts: pd.DataFrame) -> pd.DataFrame:
    df = posts.copy()
    for col in ("likes", "comments_count", "shares", "views"):
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    # One formula per platform within a dataset: shares are included only if the platform can report them AND
    # >= 95% of that platform's posts do. A post missing a required component gets interactions = null.
    share_cov = df.groupby("platform")["shares"].apply(lambda s: s.notna().mean())
    platform_uses = {p: bool(SHARES_REPORTED.get(p, False) and share_cov.get(p, 0) >= SHARE_COVERAGE_MIN)
                     for p in df["platform"].unique()}
    uses_shares = df["platform"].map(platform_uses).fillna(False).astype(bool)
    base = df["likes"].astype("Float64") + df["comments_count"].astype("Float64")
    with_shares = base + df["shares"].astype("Float64")
    df["interactions"] = with_shares.where(uses_shares, base)
    df["er_formula"] = "(likes + comments) / views"
    df.loc[uses_shares, "er_formula"] = "(likes + comments + shares) / views"
    df["er_views"] = _ratio(df["interactions"], df["views"])
    df["comment_ratio"] = _ratio(df["comments_count"], df["likes"])
    df["mature"] = df["days_since_post"].astype(int) >= MATURE_DAYS

    mature = df[df["mature"]]
    keys = ["brand", "platform"]
    med_inter = mature.groupby(keys)["interactions"].median().rename("baseline_interactions")
    med_er = mature.groupby(keys)["er_views"].median().rename("baseline_er_views")
    df = df.join(med_inter, on=keys).join(med_er, on=keys)
    df["attention_index"] = _ratio(df["interactions"], df["baseline_interactions"])
    df["er_index"] = _ratio(df["er_views"], df["baseline_er_views"])
    return df


def coverage(posts: pd.DataFrame) -> dict:
    """Share of posts where each metric is reported (null ≠ 0), overall and per platform."""
    cols = ["likes", "comments_count", "shares", "views"]
    total = len(posts)
    overall = {c: (round(float(posts[c].notna().mean()), 4) if total else None) for c in cols}
    per_platform = {
        plat: {c: round(float(g[c].notna().mean()), 4) for c in cols} | {"posts": int(len(g))}
        for plat, g in posts.groupby("platform")
    }
    return {"posts": total, "overall": overall, "per_platform": per_platform}


def apply_filters(posts: pd.DataFrame, filters: dict) -> pd.DataFrame:
    df = posts
    for key in ("platform", "brand", "campaign", "content_type"):
        values = filters.get(key)
        if values:
            df = df[df[key].isin(values if isinstance(values, (list, tuple, set)) else [values])]
    if filters.get("date_from"):
        df = df[df["published_at"] >= str(filters["date_from"])]
    if filters.get("date_to"):
        df = df[df["published_at"] <= str(filters["date_to"]) + "T23:59:59Z"]
    return df
