from datetime import UTC, datetime

import pandas as pd
import pytest

from audienceiq.data import importer

NOW = datetime(2026, 11, 15, tzinfo=UTC)


def _posts_csv(extra_rows: str = "") -> str:
    head = "Post ID,Brand Name,Network,Post Type,Likes,Comments,Shares,Plays,Publish Time,Campaign Name\n"
    rows = "".join(f"P{i},Brand A,instagram,Reel,{100 + i},{10 + i},5,{1000 + i},2026-10-0{1 + i % 9}T10:00:00Z,Eid\n"
                   for i in range(25))
    return head + rows + extra_rows


def test_header_suggestions_map_common_export_names():
    raw = importer.read_csv_text(_posts_csv(), 100)
    m = importer.suggest_mapping(list(raw.columns), importer.POST_FIELDS)
    assert m["post_id"] == "Post ID" and m["likes"] == "Likes" and m["views"] == "Plays"
    assert m["platform"] == "Network" and m["content_type"] == "Post Type" and m["published_at"] == "Publish Time"


def test_valid_posts_normalised():
    raw = importer.read_csv_text(_posts_csv(), 100)
    res = importer.validate_posts(raw, importer.suggest_mapping(list(raw.columns), importer.POST_FIELDS), NOW)
    f = res["frame"]
    assert res["rows_valid"] == 25 and res["error_count"] == 0
    assert set(f["platform"]) == {"Instagram"} and set(f["content_type"]) == {"reel"}
    assert f["days_since_post"].min() >= 0


@pytest.mark.parametrize("bad_row,field", [
    ("PX,Brand A,instagram,Reel,12%,1,0,10,2026-10-01T00:00:00Z,Eid\n", "likes"),       # percentage is not a count
    ("PX,Brand A,instagram,Reel,-5,1,0,10,2026-10-01T00:00:00Z,Eid\n", "likes"),        # negative count
    ("PX,Brand A,instagram,Reel,5,1,0,10,2031-01-01T00:00:00Z,Eid\n", "published_at"),  # future date
    ("PX,Brand A,instagram,Reel,5,1,0,10,not a date,Eid\n", "published_at"),
])
def test_invalid_values_are_reported_with_row_numbers(bad_row, field):
    raw = importer.read_csv_text(_posts_csv(bad_row), 100)
    res = importer.validate_posts(raw, importer.suggest_mapping(list(raw.columns), importer.POST_FIELDS), NOW)
    assert res["rows_valid"] == 25
    assert any(e["field"] == field and e["row"] == 27 for e in res["errors"])


def test_missing_views_stay_null_and_duplicates_removed():
    extra = "P0,Brand A,instagram,Reel,1,1,1,,2026-10-01T00:00:00Z,Eid\nP99,Brand A,fb,Photo,1,1,1,,2026-10-01T00:00:00Z,\n"
    raw = importer.read_csv_text(_posts_csv(extra), 100)
    res = importer.validate_posts(raw, importer.suggest_mapping(list(raw.columns), importer.POST_FIELDS), NOW)
    f = res["frame"].set_index("post_id")
    assert res["duplicates_removed"] == 1
    assert pd.isna(f.loc["P99", "views"]) and f.loc["P99", "platform"] == "Facebook"
    assert f.loc["P99", "content_type"] == "product_photo" and f.loc["P99", "campaign"] == "No campaign"


def test_comments_pii_columns_dropped_orphans_and_empty_skipped_unicode_kept():
    csv = ("post_id,comment,username,likes\nP1,Price kya hai?,sana_k,2\nP1,قیمت کیا ہے؟,ali,0\n"
           "P9,orphan comment,x,1\nP1,,y,0\n")
    raw = importer.read_csv_text(csv, 100)
    m = importer.suggest_mapping(list(raw.columns), importer.COMMENT_FIELDS)
    res = importer.validate_comments(raw, m, {"P1"})
    assert res["rows_valid"] == 2 and res["orphans"] == 1 and res["empty"] == 1
    assert "username" in res["pii_columns_dropped"] and "username" not in res["frame"].columns
    assert "قیمت کیا ہے؟" in set(res["frame"]["comment_text"])
    assert res["frame"]["comment_id"].str.startswith("IMP-C").all()


def test_unrecoverable_inputs_raise_readable_errors():
    with pytest.raises(importer.ImportError_, match="empty"):
        importer.read_csv_text("", 10)
    with pytest.raises(importer.ImportError_, match="no data rows"):
        importer.read_csv_text("a,b\n", 10)
    with pytest.raises(importer.ImportError_, match="Too many rows"):
        importer.read_csv_text("a\n" + "1\n" * 11, 10)
    raw = importer.read_csv_text("x,y\n1,2\n", 10)
    with pytest.raises(importer.ImportError_, match="Required post fields"):
        importer.validate_posts(raw, importer.suggest_mapping(["x", "y"], importer.POST_FIELDS), NOW)


def test_preview_readiness_and_templates():
    p = importer.preview(_posts_csv(), "post_id,comment_text\n" + "".join(f"P{i % 25},price? {i}\n" for i in range(40)))
    assert p["ready"] and p["posts"]["rows_valid"] == 25 and p["comments"]["rows_valid"] == 40
    assert importer.template_csv("posts").startswith("post_id,brand,platform")
    assert "comment_text" in importer.template_csv("comments")
