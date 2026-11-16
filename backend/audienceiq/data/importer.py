"""CSV import: preview → field mapping → validation → source attestation → confirm (persist locally).

Header suggestions and strict number parsing adapted from Repo B (signalspend-ai,
backend/src/ads_optimizer/data/schema_mapping.py @9c5f415: normalized_name, numeric_values, NULLS). Fuzzy matches are
only *suggested*; the user confirms the mapping. Author/username columns are dropped and never stored (Repo A rule).
"""

import hashlib
import io
import re
from datetime import UTC, datetime

import pandas as pd

from audienceiq.constants import CONTENT_TYPES, PLATFORMS

MAX_POST_ROWS = 10_000
MAX_COMMENT_ROWS = 60_000
MAX_COMMENT_CHARS = 2_000
MAX_ERRORS_LISTED = 50
NULLS = {"", "null", "none", "nan", "n/a", "na", "—", "-", "not available"}

POST_FIELDS = {
    "post_id": {"required": True, "aliases": ["post_id", "post id", "id", "media id", "video id", "post"]},
    "brand": {"required": True, "aliases": ["brand", "brand name", "account", "page", "page name", "channel"]},
    "platform": {"required": True, "aliases": ["platform", "network", "social network", "source platform"]},
    "published_at": {"required": True, "aliases": ["published_at", "published at", "publish time", "date", "post date",
                                                   "created time", "timestamp", "posted at", "created at"]},
    "likes": {"required": True, "aliases": ["likes", "like count", "reactions", "likes count", "like_count"]},
    "comments_count": {"required": True, "aliases": ["comments_count", "comments", "comment count", "comments count",
                                                     "comment_count"]},
    "content_type": {"required": False, "aliases": ["content_type", "content type", "post type", "media type", "format",
                                                    "type"]},
    "campaign": {"required": False, "aliases": ["campaign", "campaign name", "collection"]},
    "shares": {"required": False, "aliases": ["shares", "share count", "shares count", "share_count"]},
    "views": {"required": False, "aliases": ["views", "view count", "plays", "video views", "views count", "view_count"]},
    "product_category": {"required": False, "aliases": ["product_category", "product category", "category"]},
    "source_url": {"required": False, "aliases": ["source_url", "url", "permalink", "link", "post url"]},
    "post_text": {"required": False, "aliases": ["post_text", "caption", "text", "message", "description"]},
}
COMMENT_FIELDS = {
    "post_id": {"required": True, "aliases": ["post_id", "post id", "media id", "video id", "post"]},
    "comment_text": {"required": True, "aliases": ["comment_text", "comment", "text", "message", "comment text", "body"]},
    "comment_id": {"required": False, "aliases": ["comment_id", "comment id", "id"]},
    "published_at": {"required": False, "aliases": ["published_at", "published at", "date", "created time", "timestamp"]},
    "like_count": {"required": False, "aliases": ["like_count", "likes", "comment likes"]},
}
FORBIDDEN = {"author", "author name", "author_name", "username", "user name", "user_name", "user", "handle",
             "profile", "profile url", "profile_url", "author display name", "authordisplayname", "author channel id",
             "authorchannelid", "author channel url", "email", "phone", "user id", "user_id", "commenter", "name"}
PLATFORM_MAP = {"instagram": "Instagram", "ig": "Instagram", "insta": "Instagram", "tiktok": "TikTok", "tik tok": "TikTok",
                "tt": "TikTok", "facebook": "Facebook", "fb": "Facebook", "meta": "Facebook", "youtube": "YouTube",
                "yt": "YouTube"}
CONTENT_MAP = {"reel": "reel", "reels": "reel", "short": "video", "shorts": "video", "video": "video", "photo": "product_photo",
               "image": "product_photo", "product photo": "product_photo", "product_photo": "product_photo",
               "carousel": "product_photo", "influencer": "influencer_post", "influencer post": "influencer_post",
               "influencer_post": "influencer_post", "collab": "influencer_post", "styling": "styling_video",
               "styling video": "styling_video", "styling_video": "styling_video", "tutorial": "styling_video",
               "sale": "sale_announcement", "sale announcement": "sale_announcement", "promo": "sale_announcement",
               "sale_announcement": "sale_announcement", "other": "other"}


class ImportError_(ValueError):
    """Raised for unrecoverable input problems (size, encoding, missing required columns)."""


def normalized_name(value) -> str:
    value = re.sub(r"([a-z])([A-Z])", r"\1 \2", str(value))
    return re.sub(r"[^a-z0-9]+", " ", value.strip().lower()).strip()


def read_csv_text(text: str, max_rows: int) -> pd.DataFrame:
    if not text or not text.strip():
        raise ImportError_("The file is empty.")
    try:
        df = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False, nrows=max_rows + 1)
    except Exception as exc:  # pandas raises several parser error types
        raise ImportError_(f"Could not parse the CSV: {str(exc)[:160]}") from exc
    if len(df) > max_rows:
        raise ImportError_(f"Too many rows: the limit is {max_rows:,} per file.")
    if df.empty:
        raise ImportError_("The CSV has a header but no data rows.")
    return df


def suggest_mapping(columns: list[str], fields: dict) -> dict[str, str | None]:
    norm = {normalized_name(c): c for c in columns}
    mapping = {}
    for field, spec in fields.items():
        mapping[field] = next((norm[a] for a in (normalized_name(x) for x in spec["aliases"]) if a in norm), None)
    used = [c for c in mapping.values() if c]
    for field in mapping:  # one column may not feed two fields
        if mapping[field] and used.count(mapping[field]) > 1 and normalized_name(mapping[field]) != field.replace("_", " "):
            mapping[field] = None
    return mapping


def numeric(series: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Strict count parsing → (values Int64 with NA for empty, mask of invalid entries). '12%' is invalid, not 12."""
    text = series.astype(str).str.strip()
    empty = text.str.lower().isin(NULLS)
    cleaned = text.str.replace(r"^(?:PKR|Rs\.?)\s*", "", regex=True, flags=re.I).str.replace(",", "", regex=False)
    valid = cleaned.str.fullmatch(r"[+-]?\d+(?:\.0+)?")
    values = pd.to_numeric(cleaned.where(valid & ~empty), errors="coerce").astype("Int64")
    return values, ~(valid | empty)


def _errors_add(errors: list, row: int | None, field: str, message: str) -> None:
    if len(errors) < MAX_ERRORS_LISTED:
        errors.append({"row": row, "field": field, "message": message})


def validate_posts(raw: pd.DataFrame, mapping: dict, snapshot: datetime) -> dict:
    errors, warnings = [], []
    missing = [f for f, s in POST_FIELDS.items() if s["required"] and not mapping.get(f)]
    if missing:
        raise ImportError_(f"Required post fields are not mapped: {', '.join(missing)}.")
    df = pd.DataFrame({f: raw[c] if c else None for f, c in mapping.items() if f in POST_FIELDS})
    n_errors = 0
    for col in ("likes", "comments_count", "shares", "views"):
        if col in df and mapping.get(col):
            vals, bad = numeric(df[col])
            neg = vals.fillna(0) < 0
            for i in df.index[bad | neg]:
                n_errors += 1
                _errors_add(errors, int(i) + 2, col, f"'{df.at[i, col]}' is not a non-negative whole number.")
            df[col] = vals.where(~neg)
        else:
            df[col] = pd.array([pd.NA] * len(df), dtype="Int64")
    df["platform_raw"] = df["platform"].astype(str)
    df["platform"] = df["platform"].astype(str).str.strip().str.lower().map(PLATFORM_MAP).fillna("Other")
    unknown_plat = (df["platform"] == "Other").sum()
    if unknown_plat:
        warnings.append(f"{unknown_plat} posts have an unrecognised platform and were set to 'Other'.")
    if mapping.get("content_type"):
        df["content_type_raw"] = df["content_type"].astype(str)
        df["content_type"] = df["content_type"].astype(str).str.strip().str.lower().map(CONTENT_MAP).fillna("unknown")
        unk = (df["content_type"] == "unknown").sum()
        if unk:
            warnings.append(f"{unk} posts have an unrecognised content type; kept as 'unknown' (raw value preserved).")
    else:
        df["content_type"], df["content_type_raw"] = "unknown", None
        warnings.append("No content-type column mapped: all posts are 'unknown' and Q1 format comparisons are unavailable.")
    published = pd.to_datetime(df["published_at"], errors="coerce", utc=True)
    for i in df.index[published.isna()]:
        n_errors += 1
        _errors_add(errors, int(i) + 2, "published_at", f"'{df.at[i, 'published_at']}' is not a recognised date/time.")
    future = published > pd.Timestamp(snapshot)
    for i in df.index[future.fillna(False)]:
        n_errors += 1
        _errors_add(errors, int(i) + 2, "published_at", "Date is in the future relative to the import time.")
    df["published_at"] = published.dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    df["days_since_post"] = (pd.Timestamp(snapshot) - published).dt.days
    df["post_id"] = df["post_id"].astype(str).str.strip()
    blank_id = df["post_id"].str.lower().isin(NULLS)
    for i in df.index[blank_id]:
        n_errors += 1
        _errors_add(errors, int(i) + 2, "post_id", "Missing post_id.")
    dup = df["post_id"].duplicated(keep="first") & ~blank_id
    if dup.any():
        warnings.append(f"{int(dup.sum())} duplicate post_id rows were removed (first occurrence kept).")
    df["campaign"] = df["campaign"].replace("", None).fillna("No campaign") if mapping.get("campaign") else "No campaign"
    df["product_category"] = (df["product_category"].replace("", None).fillna("Unspecified")
                              if mapping.get("product_category") else "Unspecified")
    df["brand"] = df["brand"].astype(str).str.strip().replace("", "Unknown brand")
    for opt in ("source_url", "post_text"):
        if not mapping.get(opt):
            df[opt] = None
    invalid_row = published.isna() | future.fillna(False) | blank_id
    for col in ("likes", "comments_count"):
        invalid_row |= df[col].isna() & raw[mapping[col]].astype(str).str.strip().str.lower().map(lambda v: v not in NULLS)
    clean = df[~invalid_row & ~dup].copy()
    if mapping.get("views") and clean["views"].notna().any():
        impossible = clean["likes"].astype("Float64") > clean["views"].astype("Float64") * 2
        if impossible.fillna(False).any():
            warnings.append(f"{int(impossible.fillna(False).sum())} posts have more than twice as many likes as views "
                            "(possible data error); kept but worth checking.")
    missing_share = {c: round(float(clean[c].isna().mean()), 4) for c in ("likes", "comments_count", "shares", "views")}
    return {"frame": clean, "errors": errors, "error_count": n_errors, "warnings": warnings, "rows_read": int(len(raw)),
            "rows_valid": int(len(clean)), "duplicates_removed": int(dup.sum()), "missing_share": missing_share,
            "platforms": clean["platform"].value_counts().to_dict(),
            "content_types": clean["content_type"].value_counts().to_dict()}


def validate_comments(raw: pd.DataFrame, mapping: dict, post_ids: set[str] | None) -> dict:
    errors, warnings = [], []
    missing = [f for f, s in COMMENT_FIELDS.items() if s["required"] and not mapping.get(f)]
    if missing:
        raise ImportError_(f"Required comment fields are not mapped: {', '.join(missing)}.")
    dropped_pii = [c for c in raw.columns if normalized_name(c) in FORBIDDEN and c not in mapping.values()]
    if dropped_pii:
        warnings.append(f"Removed personal-identity columns (never stored): {', '.join(dropped_pii)}.")
    df = pd.DataFrame({f: raw[c] if c else None for f, c in mapping.items() if f in COMMENT_FIELDS})
    df["post_id"] = df["post_id"].astype(str).str.strip()
    text = df["comment_text"].astype(str)
    empty = text.str.strip().eq("") | text.str.strip().str.lower().isin({"nan", "null"})
    too_long = text.str.len() > MAX_COMMENT_CHARS
    if empty.any():
        warnings.append(f"{int(empty.sum())} empty comments were skipped.")
    for i in df.index[too_long]:
        _errors_add(errors, int(i) + 2, "comment_text", f"Comment longer than {MAX_COMMENT_CHARS:,} characters; truncated.")
    df["comment_text"] = text.str.slice(0, MAX_COMMENT_CHARS)
    if mapping.get("comment_id"):
        df["comment_id"] = df["comment_id"].astype(str).str.strip()
    else:
        df["comment_id"] = None
    gen = df["comment_id"].isna() | df["comment_id"].astype(str).str.lower().isin(NULLS)
    df.loc[gen, "comment_id"] = [
        "IMP-C" + hashlib.sha256(f"{p}|{t}|{i}".encode()).hexdigest()[:12]
        for i, (p, t) in enumerate(zip(df.loc[gen, "post_id"], df.loc[gen, "comment_text"], strict=True))]
    # Never keep raw platform comment IDs that could be looked up: store a salted hash instead.
    df.loc[~gen, "comment_id"] = ["IMP-C" + hashlib.sha256(f"aiq|{c}".encode()).hexdigest()[:12] for c in df.loc[~gen, "comment_id"]]
    dup = df["comment_id"].duplicated(keep="first")
    if dup.any():
        warnings.append(f"{int(dup.sum())} duplicate comments were removed.")
    orphan = ~df["post_id"].isin(post_ids) if post_ids is not None else pd.Series(False, index=df.index)
    if orphan.any():
        warnings.append(f"{int(orphan.sum())} comments reference a post_id that is not in the posts file and were skipped "
                        "(join mismatch).")
    if mapping.get("like_count"):
        vals, bad = numeric(df["like_count"])
        df["like_count"] = vals
        if bad.any():
            warnings.append(f"{int(bad.sum())} comment like counts were not whole numbers and were set to unknown.")
    else:
        df["like_count"] = pd.array([pd.NA] * len(df), dtype="Int64")
    if mapping.get("published_at"):
        ts = pd.to_datetime(df["published_at"], errors="coerce", utc=True)
        df["published_at"] = ts.dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        df["published_at"] = None
    clean = df[~empty & ~dup & ~orphan].copy()
    return {"frame": clean, "errors": errors, "error_count": len(errors), "warnings": warnings, "rows_read": int(len(raw)),
            "rows_valid": int(len(clean)), "orphans": int(orphan.sum()), "empty": int(empty.sum()),
            "duplicates_removed": int(dup.sum()), "pii_columns_dropped": dropped_pii}


def preview(posts_text: str | None, comments_text: str | None, posts_mapping: dict | None = None,
            comments_mapping: dict | None = None) -> dict:
    snapshot = datetime.now(UTC)
    out: dict = {"snapshot_at": snapshot.isoformat(timespec="seconds"), "posts": None, "comments": None, "ready": False}
    post_ids = None
    if posts_text:
        raw = read_csv_text(posts_text, MAX_POST_ROWS)
        mapping = {**suggest_mapping(list(raw.columns), POST_FIELDS), **(posts_mapping or {})}
        res = validate_posts(raw, mapping, snapshot)
        post_ids = set(res["frame"]["post_id"])
        out["posts"] = _public(res, raw, mapping, POST_FIELDS)
    if comments_text:
        raw = read_csv_text(comments_text, MAX_COMMENT_ROWS)
        mapping = {**suggest_mapping(list(raw.columns), COMMENT_FIELDS), **(comments_mapping or {})}
        res = validate_comments(raw, mapping, post_ids)
        out["comments"] = _public(res, raw, mapping, COMMENT_FIELDS)
    out["ready"] = bool(out["posts"] and out["posts"]["rows_valid"] >= 20 and out["comments"]
                        and out["comments"]["rows_valid"] >= 30)
    if not out["ready"]:
        out["ready_reason"] = ("Need at least 20 valid posts and 30 valid comments that join to them for a meaningful "
                               "analysis.")
    return out


def _public(res: dict, raw: pd.DataFrame, mapping: dict, fields: dict) -> dict:
    frame = res["frame"]
    sample = frame.head(8).astype(object).where(pd.notna(frame.head(8)), None).to_dict(orient="records")
    return {k: v for k, v in res.items() if k != "frame"} | {
        "columns": list(raw.columns), "mapping": mapping,
        "fields": {f: {"required": s["required"]} for f, s in fields.items()}, "sample": sample}


def template_csv(kind: str) -> str:
    if kind == "posts":
        return ("post_id,brand,platform,campaign,content_type,product_category,likes,comments_count,shares,views,"
                "published_at,source_url\n"
                "P001,Brand A,Instagram,Eid Collection,reel,Women's lawn suits,1250,186,95,25000,2026-03-10T15:00:00Z,\n"
                "P002,Brand A,Facebook,Eid Collection,product_photo,Women's lawn suits,640,72,18,,2026-03-11T12:30:00Z,\n")
    if kind == "comments":
        return ("post_id,comment_id,comment_text,published_at,like_count\n"
                "P001,C0001,Price please?,2026-03-10T16:00:00Z,2\n"
                "P001,C0002,Delivery kitne din mein hogi?,2026-03-10T17:10:00Z,0\n"
                "P002,C0003,Is this available in Karachi?,2026-03-11T13:00:00Z,1\n")
    raise KeyError(kind)


VALID_PLATFORMS = set(PLATFORMS)
VALID_CONTENT_TYPES = set(CONTENT_TYPES)
