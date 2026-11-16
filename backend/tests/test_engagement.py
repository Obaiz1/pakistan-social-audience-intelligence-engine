import math

import pandas as pd
import pytest

from audienceiq.analytics.content import compare, weighted_er
from audienceiq.analytics.engagement import add_engagement, apply_filters, coverage


def _posts(rows):
    base = {"brand": "Brand A", "campaign": "X", "content_type": "reel", "published_at": "2026-01-01T00:00:00Z",
            "days_since_post": 30, "shares": None, "views": None}
    return pd.DataFrame([{**base, **r} for r in rows])


def test_hand_calculated_engagement_rate():
    df = add_engagement(_posts([
        {"post_id": "a", "platform": "TikTok", "likes": 100, "comments_count": 20, "shares": 30, "views": 1000},
        {"post_id": "b", "platform": "YouTube", "likes": 50, "comments_count": 10, "views": 2000},
    ]))
    a, b = df.set_index("post_id").loc["a"], df.set_index("post_id").loc["b"]
    assert a["interactions"] == 150 and math.isclose(a["er_views"], 0.15)
    assert b["interactions"] == 60 and math.isclose(b["er_views"], 0.03)       # YouTube formula excludes shares
    assert a["er_formula"] == "(likes + comments + shares) / views"
    assert b["er_formula"] == "(likes + comments) / views"


def test_missing_is_not_zero():
    df = add_engagement(_posts([
        {"post_id": "photo", "platform": "Instagram", "likes": 10, "comments_count": 2, "shares": 1, "views": None},
        {"post_id": "zero", "platform": "Instagram", "likes": 10, "comments_count": 2, "shares": 1, "views": 0},
        {"post_id": "hidden", "platform": "Instagram", "likes": None, "comments_count": 2, "shares": 1, "views": 100},
    ])).set_index("post_id")
    assert pd.isna(df.loc["photo", "er_views"])            # no views reported -> no rate
    assert pd.isna(df.loc["zero", "er_views"])             # zero denominator -> null, not inf/0
    assert pd.isna(df.loc["hidden", "interactions"])       # hidden likes -> unknown interactions
    assert pd.isna(df.loc["hidden", "comment_ratio"])


def test_share_coverage_rule_keeps_one_formula_per_platform():
    rows = [{"post_id": f"p{i}", "platform": "Instagram", "likes": 10, "comments_count": 1, "shares": 2, "views": 100}
            for i in range(10)]
    rows[0]["shares"] = None                                # 90% coverage < 95% -> shares dropped for the platform
    df = add_engagement(_posts(rows))
    assert (df["er_formula"] == "(likes + comments) / views").all()
    assert (df["interactions"] == 11).all()


def test_attention_index_baseline_uses_mature_posts_only():
    rows = [{"post_id": f"m{i}", "platform": "Facebook", "likes": v, "comments_count": 0, "shares": 0}
            for i, v in enumerate([10, 20, 30])]
    rows.append({"post_id": "new", "platform": "Facebook", "likes": 1000, "comments_count": 0, "shares": 0, "days_since_post": 2})
    df = add_engagement(_posts(rows)).set_index("post_id")
    assert df.loc["m1", "baseline_interactions"] == 20       # median of mature 10,20,30
    assert math.isclose(df.loc["m2", "attention_index"], 1.5)
    assert not df.loc["new", "mature"]


def test_weighted_er_is_ratio_of_sums_not_mean_of_ratios():
    df = add_engagement(_posts([
        {"post_id": "a", "platform": "TikTok", "likes": 10, "comments_count": 0, "shares": 0, "views": 100},
        {"post_id": "b", "platform": "TikTok", "likes": 900, "comments_count": 0, "shares": 0, "views": 10000},
    ]))
    assert math.isclose(weighted_er(df), 910 / 10100)


def test_compare_marks_small_groups_untested():
    rows = [{"post_id": f"r{i}", "platform": "TikTok", "content_type": "reel" if i < 25 else "video",
             "likes": 100 + i, "comments_count": 5, "shares": 1, "views": 1000} for i in range(30)]
    out = compare(add_engagement(_posts(rows)), "content_type", "attention_index")
    by = {r["group"]: r for r in out["rows"]}
    assert by["reel"]["sufficient"] and not by["video"]["sufficient"]
    assert by["video"]["p_value"] is None


def test_filters_and_coverage():
    df = add_engagement(_posts([
        {"post_id": "a", "platform": "TikTok", "likes": 1, "comments_count": 1, "shares": 1, "views": 10},
        {"post_id": "b", "platform": "YouTube", "likes": 1, "comments_count": 1, "views": 10},
    ]))
    assert list(apply_filters(df, {"platform": ["YouTube"]})["post_id"]) == ["b"]
    cov = coverage(df)
    assert cov["overall"]["shares"] == 0.5 and cov["per_platform"]["YouTube"]["shares"] == 0.0


@pytest.mark.parametrize("bad", [-1])
def test_negative_counts_never_produced_by_generator(bad):
    from audienceiq.data.synthetic import generate

    p = generate(120, 3).posts
    for col in ("likes", "comments_count", "shares", "views"):
        assert (p[col].dropna() > bad).all()
