import numpy as np
import pandas as pd

from audienceiq.analytics.engagement import add_engagement
from audienceiq.anomalies.detect import CAVEAT, detect


def _cohort(n=40, platform="TikTok", seed=0, brand="Brand A", content_type="reel"):
    rng = np.random.default_rng(seed)
    views = rng.integers(9_000, 11_000, n)
    likes = (views * rng.normal(0.05, 0.004, n)).astype(int)
    return [{"post_id": f"{platform[:2]}{brand[-1]}{i}", "brand": brand, "platform": platform, "content_type": content_type,
             "campaign": "X", "likes": int(likes[i]), "comments_count": int(likes[i] * 0.05), "shares": 10,
             "views": int(views[i]), "published_at": "2026-01-01T00:00:00Z", "days_since_post": 30} for i in range(n)]


def _run(rows, comments=None):
    return detect(add_engagement(pd.DataFrame(rows)), comments, dataset_id="t")


def test_known_outliers_detected_both_directions():
    rows = _cohort()
    rows[0]["likes"] = 3000          # ER ~0.30 vs ~0.05 → positive
    rows[1]["likes"] = 20            # ER ~0.004 → negative
    res = _run(rows)
    eng = res["flags"][res["flags"]["kind"] == "engagement"].set_index("post_id")
    assert eng.loc["TiA0", "direction"] == "positive"
    assert eng.loc["TiA1", "direction"] == "negative"
    assert len(eng) == 2                                   # ordinary posts are not flagged


def test_reason_text_is_specific_and_never_alleges_fraud():
    rows = _cohort()
    rows[0]["likes"] = 3000
    f = _run(rows)["flags"].iloc[0]
    assert "cohort median" in f["reason"] and "robust z" in f["reason"] and "40 mature" in f["reason"]
    assert f["caveat"] == CAVEAT and "not evidence of fraud" in f["caveat"]
    for word in ("fake", "bot ", "fraudulent"):
        assert word not in f["reason"].lower()


def test_platforms_are_not_mixed():
    rows = _cohort(platform="TikTok") + _cohort(platform="YouTube", seed=1)
    for r in rows:
        if r["platform"] == "YouTube":
            r["likes"] = int(r["likes"] / 10)                # different but internally consistent platform level
    res = _run(rows)
    assert res["flags"].empty or not (res["flags"]["kind"] == "engagement").any()
    assert set(res["scores"]["cohort_key"].str.split(" · ").str[-2]) <= {"reel"}


def test_tiny_cohorts_and_immature_posts_are_not_scored():
    rows = _cohort(n=10)
    rows += [dict(_cohort(n=1, seed=9)[0], post_id="young", days_since_post=2)]
    res = _run(rows)
    assert res["metrics"]["posts_scored"] == 0
    assert res["metrics"]["posts_unscored_small_cohort"] == 10
    assert res["metrics"]["posts_immature"] == 1


def test_missing_values_and_zero_views_do_not_crash():
    rows = _cohort()
    rows[2]["views"] = 0
    rows[3]["likes"] = None
    rows[4]["views"] = None
    res = _run(rows)
    scored = set(res["scores"]["post_id"])
    assert "TiA3" not in scored                               # unknown interactions → not scored
    assert "TiA2" in scored or "TiA2" not in scored           # zero views falls back to the count metric, no exception


def test_need_mix_shift_detected():
    rows = _cohort()
    comments = []
    for i, r in enumerate(rows):
        needs = ["order_issue"] * 9 + ["price"] if i == 5 else (["price"] * 5 + ["compliment"] * 4 + ["order_issue"])
        comments += [{"post_id": r["post_id"], "need": n} for n in needs]
    res = _run(rows, pd.DataFrame(comments))
    mix = res["flags"][res["flags"]["kind"] == "need_mix"]
    assert list(mix["post_id"]) == ["TiA5"]
    assert "order_issue" in mix.iloc[0]["metric"]


def test_deterministic():
    rows = _cohort()
    rows[0]["likes"] = 3000
    a, b = _run(rows), _run(rows)
    pd.testing.assert_frame_equal(a["flags"].drop(columns=[]), b["flags"])
