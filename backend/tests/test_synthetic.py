import pandas as pd
import pytest

from audienceiq.data.synthetic import generate


@pytest.fixture(scope="module")
def corpus():
    return generate(400, seed=5)


def test_deterministic(corpus):
    again = generate(400, seed=5)
    pd.testing.assert_frame_equal(corpus.posts, again.posts)
    pd.testing.assert_frame_equal(corpus.comments, again.comments)
    assert not generate(400, seed=6).posts.equals(corpus.posts)


def test_ids_unique_and_joined(corpus):
    assert corpus.posts["post_id"].is_unique
    assert corpus.comments["comment_id"].is_unique
    assert corpus.comments["post_id"].isin(corpus.posts["post_id"]).all()
    assert corpus.posts["post_id"].str.startswith("SYN-P").all()


def test_retained_comments_never_exceed_platform_count(corpus):
    retained = corpus.comments.groupby("post_id").size()
    reported = corpus.posts.set_index("post_id")["comments_count"]
    assert (retained <= reported.reindex(retained.index)).all()


def test_platform_metric_availability(corpus):
    p = corpus.posts
    assert p.loc[p["platform"] == "YouTube", "shares"].isna().all()           # YouTube API reports no shares
    photos = p[p["content_type"].isin(["product_photo", "sale_announcement"]) & p["platform"].isin(["Instagram", "Facebook"])]
    assert photos["views"].isna().all()                                          # photos have no views
    assert p.loc[p["platform"] == "TikTok", "views"].notna().all()


def test_single_category_and_fictional_brands(corpus):
    assert corpus.posts["product_category"].nunique() == 1
    assert set(corpus.posts["brand"]) <= {f"Brand {c}" for c in "ABCDEF"}
    for real in ("Khaadi", "Sapphire", "Gul Ahmed"):
        assert not corpus.posts["post_text"].str.contains(real).any()


def test_injected_anomalies_scale_and_are_mature(corpus):
    inj = corpus.truth_posts[corpus.truth_posts["injected_anomaly"] != ""]
    assert 0.02 <= len(inj) / len(corpus.posts) <= 0.05
    ages = corpus.posts.set_index("post_id").loc[inj["post_id"], "days_since_post"]
    assert (ages >= 10).all()


def test_languages_present(corpus):
    assert set(corpus.truth_comments["true_language"]) == {"english", "roman_urdu", "urdu", "mixed"}


def test_size_bounds():
    with pytest.raises(ValueError):
        generate(10)
