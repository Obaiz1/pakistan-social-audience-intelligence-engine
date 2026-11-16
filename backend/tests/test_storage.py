import sqlite3

import pandas as pd
import pytest

from audienceiq.storage import db

DATASET = {"dataset_id": "d1", "name": "t", "mode": "synthetic", "created_at": "2026-01-01", "snapshot_at": "2026-01-02",
           "text_permission": "illustrative", "disclaimer": "SYNTHETIC", "post_count": 1, "comment_count": 1,
           "sources": [{"source_id": "S", "source_type": "synthetic_generator", "name": "g", "collection_method": "sim",
                        "reuse_permission": "free"}]}


def _post(**kw):
    base = {"post_id": "P1", "source_id": "S", "source_post_id": "P1", "brand": "A", "platform": "Instagram",
            "campaign": "X", "content_type": "reel", "product_category": "lawn", "likes": 1, "comments_count": 1,
            "published_at": "2026-01-01", "snapshot_at": "2026-01-02", "days_since_post": 1, "source_type": "synthetic_generator",
            "dataset_origin": "synthetic", "collection_method": "sim", "reuse_permission": "free",
            "observed_vs_synthetic": "synthetic"}
    return {**base, **kw}


def _comment(**kw):
    base = {"comment_id": "C1", "post_id": "P1", "comment_text": "price?", "text_permission": "illustrative",
            "language_type": "english", "topic": "price", "sentiment": "neutral", "purchase_intent": "possible_inquiry",
            "char_len": 6, "source": "synthetic_generator"}
    return {**base, **kw}


def _load(posts, comments):
    conn = db.connect(":memory:")
    db.load_bundle(conn, DATASET, {"posts": pd.DataFrame(posts), "comments": pd.DataFrame(comments)})
    return conn


def test_valid_bundle_loads():
    conn = _load([_post()], [_comment()])
    assert conn.execute("SELECT COUNT(*) FROM comments").fetchone()[0] == 1


@pytest.mark.parametrize("posts,comments", [
    ([_post(), _post()], [_comment()]),                         # duplicate post id
    ([_post()], [_comment(post_id="P404")]),                    # orphan comment (FK)
    ([_post(likes=-1)], [_comment()]),                          # negative count (CHECK)
    ([_post(platform="MySpace")], [_comment()]),                # unknown platform (CHECK)
    ([_post()], [_comment(language_type="klingon")]),           # invalid language code
])
def test_constraints_reject_bad_rows(posts, comments):
    with pytest.raises(sqlite3.IntegrityError):
        _load(posts, comments)


def test_null_metrics_are_allowed_and_stay_null():
    conn = _load([_post(views=None, shares=None)], [_comment()])
    assert conn.execute("SELECT views, shares FROM posts").fetchone() == (None, None)


def test_bundle_roundtrip_and_manifest(tmp_path):
    tables = {"posts": pd.DataFrame([_post(views=None)]), "comments": pd.DataFrame([_comment()])}
    db.write_bundle_dir(tmp_path / "d1", DATASET, tables, {"evaluation.json": {"ok": True}})
    assert db.verify_manifest(tmp_path / "d1") == []
    meta, read = db.read_bundle_dir(tmp_path / "d1")
    assert meta["dataset_id"] == "d1" and pd.isna(read["posts"].loc[0, "views"])
    (tmp_path / "d1" / "posts.csv").write_text("tampered", encoding="utf-8")
    assert db.verify_manifest(tmp_path / "d1") == ["posts.csv"]
