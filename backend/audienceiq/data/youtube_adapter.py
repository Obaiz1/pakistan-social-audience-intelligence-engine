"""Map YouTube Data API items to the Project 3 post/comment schema (adapted from Repo A src/processing/normalize.py and
src/processing/features.py @957e3b6f).

Honesty rules: platform = YouTube; content_type = 'video' (the API has no Shorts/reel flag, so no reel claim);
campaign is inferred from title + description keywords and labelled as such; shares are not reported by the API (null);
hidden like counts stay null; comment IDs are re-hashed and author fields are never read.
"""

import hashlib
import re
from datetime import datetime

import pandas as pd

_URDU = re.compile(r"[؀-ۿ]")
CAMPAIGN_NAMES = {"eid": "Eid", "ramadan": "Ramadan", "sale": "Sale / discount", "new_arrivals": "New arrivals",
                  "lawn_summer": "Lawn / summer", "winter": "Winter", "wedding_festive": "Wedding / festive",
                  "independence": "Independence (Azadi)", "kids": "Kids", "men": "Menswear"}
CAMPAIGN_PRIORITY = ["eid", "ramadan", "independence", "wedding_festive", "sale", "lawn_summer", "winter", "new_arrivals",
                     "kids", "men"]


def build_matchers(tags: dict[str, list[str]]) -> dict[str, re.Pattern]:
    out = {}
    for tag, words in tags.items():
        parts = []
        for w in words:
            esc = re.escape(w.lower())
            if _URDU.search(w):
                parts.append(esc)
                continue
            parts.append(f"{r'(?<!\w)' if w[0].isalnum() else ''}{esc}{r'(?!\w)' if w[-1].isalnum() else ''}")
        out[tag] = re.compile("|".join(parts))
    return out


def infer_campaign(text: str, matchers: dict[str, re.Pattern]) -> str:
    low = (text or "").lower()
    found = [t for t in CAMPAIGN_PRIORITY if t in matchers and matchers[t].search(low)]
    return CAMPAIGN_NAMES[found[0]] if found else "No campaign keyword"


def videos_to_posts(items: list[dict], brand_by_channel: dict[str, str], snapshot: datetime,
                    tags: dict[str, list[str]]) -> pd.DataFrame:
    matchers = build_matchers(tags)
    rows = []
    for v in items:
        s, st = v["snippet"], v.get("statistics", {})
        published = datetime.fromisoformat(s["publishedAt"].replace("Z", "+00:00"))
        text = f"{s.get('title', '')}\n{s.get('description', '')}"
        rows.append({
            "post_id": f"YT-{v['id']}", "source_post_id": v["id"], "brand": brand_by_channel[s["channelId"]],
            "platform": "YouTube", "campaign": infer_campaign(text, matchers), "content_type": "video",
            "content_type_raw": "youtube_video", "product_category": "Pakistani clothing (brand channel)",
            "likes": int(st["likeCount"]) if "likeCount" in st else None,
            "comments_count": int(st["commentCount"]) if "commentCount" in st else None,
            "shares": None, "views": int(st["viewCount"]) if "viewCount" in st else None,
            "published_at": published.isoformat().replace("+00:00", "Z"),
            "days_since_post": max(0, (snapshot - published).days),
            "source_url": f"https://www.youtube.com/watch?v={v['id']}", "post_text": None,
        })
    df = pd.DataFrame(rows)
    for col in ("likes", "comments_count", "shares", "views"):
        df[col] = df[col].astype("Int64")
    # Disabled comments (no commentCount) are a structural zero for the engagement numerator (Repo A ADR-015).
    df["comments_count"] = df["comments_count"].fillna(0)
    return df


def comments_to_rows(comments: list[dict]) -> pd.DataFrame:
    rows = [{"comment_id": "YT-C" + hashlib.sha256(f"aiq|{c['comment_id_hash']}".encode()).hexdigest()[:14],
             "post_id": f"YT-{c['video_id']}", "comment_text": c.get("text") or "",
             # Repo A's client returns the timestamp as `published_at_utc` (fixed after the first observed collection
             # stored no comment dates; regression test in test_youtube_adapter.py).
             "published_at": c.get("published_at_utc") or c.get("published_at"),
             "like_count": c.get("like_count")} for c in comments]
    df = pd.DataFrame(rows, columns=["comment_id", "post_id", "comment_text", "published_at", "like_count"])
    df["like_count"] = pd.to_numeric(df["like_count"], errors="coerce").astype("Int64")
    return df.drop_duplicates("comment_id")
