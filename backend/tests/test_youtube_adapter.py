from datetime import UTC, datetime

from audienceiq.data.youtube import YouTubeClient
from audienceiq.data.youtube_adapter import build_matchers, comments_to_rows, infer_campaign, videos_to_posts

TAGS = {"eid": ["eid", "عید"], "sale": ["sale", "% off"], "lawn_summer": ["lawn"]}


class _FakeResp:
    status_code = 200

    def __init__(self, payload):
        self._p = payload

    def json(self):
        return self._p


class _FakeSession:
    """Returns one commentThreads page shaped like the real YouTube Data API v3 response."""

    def get(self, url, params=None, timeout=None):
        return _FakeResp({"items": [{"snippet": {"topLevelComment": {"id": "Ugx123", "snippet": {
            "publishedAt": "2026-10-01T10:20:30Z", "textOriginal": "Price kya hai?", "likeCount": 3,
            "authorDisplayName": "SHOULD NEVER BE STORED"}}}}]})


def test_comment_dates_and_privacy_survive_the_client_to_adapter_path():
    raw = YouTubeClient("dummy-key", session=_FakeSession()).get_comments("vid1")
    df = comments_to_rows(raw)
    row = df.iloc[0]
    assert row["published_at"] == "2026-10-01T10:20:30Z"        # regression: dates were dropped (wrong key name)
    assert row["post_id"] == "YT-vid1" and row["comment_text"] == "Price kya hai?"
    assert row["comment_id"].startswith("YT-C") and "Ugx123" not in row["comment_id"]
    assert "author" not in " ".join(df.columns).lower()


def test_videos_become_youtube_video_posts_without_invented_metrics():
    item = {"id": "abc", "snippet": {"channelId": "UC1", "publishedAt": "2026-10-01T00:00:00Z",
                                     "title": "Eid Lawn Collection", "description": ""},
            "statistics": {"viewCount": "1000", "likeCount": "50"}}           # comments disabled, no shares
    p = videos_to_posts([item], {"UC1": "Khaadi"}, datetime(2026, 11, 16, tzinfo=UTC), TAGS).iloc[0]
    assert p["platform"] == "YouTube" and p["content_type"] == "video"          # never claimed to be a reel
    assert p["campaign"] == "Eid" and p["views"] == 1000 and p["comments_count"] == 0
    assert p["shares"] is None or str(p["shares"]) == "<NA>"
    assert p["source_url"] == "https://www.youtube.com/watch?v=abc" and p["days_since_post"] == 46


def test_campaign_inference_falls_back_honestly():
    m = build_matchers(TAGS)
    assert infer_campaign("Flat 30% off sale", m) == "Sale / discount"
    assert infer_campaign("Behind the scenes", m) == "No campaign keyword"
