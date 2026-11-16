"""Dataset quality & provenance audit (served at /api/v1/data/quality)."""

from datetime import UTC, datetime

import pandas as pd

from audienceiq.constants import LANGUAGE_LABELS

REQUIRED_POST_FIELDS = ["post_id", "brand", "platform", "campaign", "content_type", "product_category", "likes",
                        "comments_count", "shares", "views", "days_since_post"]
REQUIRED_COMMENT_FIELDS = ["post_id", "comment_text", "language_type", "topic", "sentiment", "purchase_intent"]


def quality_report(f) -> dict:
    p, c = f.posts, f.comments
    snap = pd.Timestamp(f.meta["snapshot_at"])
    published = pd.to_datetime(p["published_at"], utc=True, errors="coerce")
    checks = []

    def check(name: str, ok: bool, detail: str, severity: str = "error"):
        checks.append({"check": name, "passed": bool(ok), "detail": detail, "severity": "info" if ok else severity})

    dup_posts = int(p["post_id"].duplicated().sum())
    check("Unique post IDs", dup_posts == 0, f"{dup_posts} duplicates")
    dup_comments = int(c["comment_id"].duplicated().sum())
    check("Unique comment IDs", dup_comments == 0, f"{dup_comments} duplicates")
    orphans = int((~c["post_id"].isin(p["post_id"])).sum())
    check("Every comment joins to a post", orphans == 0, f"{orphans} orphan comments")
    negatives = int(sum((p[col].astype("Float64") < 0).sum() for col in ("likes", "comments_count", "shares", "views")))
    check("No negative counts", negatives == 0, f"{negatives} negative values")
    future = int((published > snap).sum())
    check("No posts after the snapshot", future == 0, f"{future} future-dated posts")
    retained = c.groupby("post_id").size()
    over = int((retained > p.set_index("post_id")["comments_count"].reindex(retained.index).astype("Float64")).sum())
    check("Retained comments ≤ platform comment count", over == 0, f"{over} posts with more retained comments than reported",
          "warning")
    unknown_lang = float((c["language_type"].isin(["unknown", "other"])).mean()) if len(c) else 0
    check("Language identified for most comments", unknown_lang < 0.25,
          f"{unknown_lang:.1%} of comments are emoji-only/other/unknown", "warning")
    immature = int((p["days_since_post"].astype(int) < 7).sum())
    check("Mature posts dominate", immature / max(len(p), 1) < 0.2, f"{immature} posts younger than 7 days (excluded from "
          "comparisons)", "warning")

    missing = {col: {"missing": int(p[col].isna().sum()), "share": round(float(p[col].isna().mean()), 4),
                     "zeros": int((p[col].astype("Float64") == 0).sum()) if col in ("likes", "comments_count", "shares", "views") else None}
               for col in REQUIRED_POST_FIELDS if col in p}
    missing_c = {col: {"missing": int(c[col].isna().sum()), "share": round(float(c[col].isna().mean()), 4)}
                 for col in REQUIRED_COMMENT_FIELDS if col in c}
    expires = f.meta.get("expires_at")
    return {
        "checks": checks, "passed": all(ch["passed"] or ch["severity"] != "error" for ch in checks),
        "posts": {"total": int(len(p)), "platforms": p["platform"].value_counts().to_dict(),
                  "brands": p["brand"].value_counts().to_dict(), "content_types": p["content_type"].value_counts().to_dict(),
                  "campaigns": int(p["campaign"].nunique()), "date_min": str(published.min())[:10],
                  "date_max": str(published.max())[:10], "missing": missing},
        "comments": {"total": int(len(c)), "posts_with_comments": int(c["post_id"].nunique()),
                     "text_permission": f.meta["text_permission"],
                     "languages": {LANGUAGE_LABELS.get(k, k): int(v) for k, v in c["language_type"].value_counts().items()},
                     "missing": missing_c, "median_chars": float(c["char_len"].median()) if len(c) else None},
        "provenance": {"mode": f.meta["mode"], "disclaimer": f.meta["disclaimer"], "snapshot_at": f.meta["snapshot_at"],
                       "expires_at": expires, "sources": f.meta.get("sources", []),
                       "seed": f.meta.get("seed"), "generator_version": f.meta.get("generator_version"),
                       "checked_at": datetime.now(UTC).isoformat(timespec="seconds")},
        "pipeline": [{"step": r["step"], "status": r["status"]} for r in f.pipeline_runs.to_dict(orient="records")],
    }
