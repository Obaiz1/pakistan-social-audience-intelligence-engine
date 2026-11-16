"""Collect an OBSERVED snapshot from the YouTube Data API v3 and build the privacy-safe observed bundle.

    YOUTUBE_API_KEY=... python pipelines/collect_youtube.py [--months 24] [--env-file path/to/.env]

- Official channels are pinned by channel ID (config/youtube_channels.yaml, from Repo A's verified audit).
- Only public data via the official API (no scraping); comment authors are never requested or stored.
- Raw comment text is written ONLY to data/observed/private/<date>/ (git-ignored) so clustering can run locally.
- The shipped bundle (data/datasets/observed-youtube-<date>/) holds post statistics and comment-level DERIVED fields
  (language, cluster, reference topic) with comment_text = NULL, salted comment IDs and date-only timestamps, and an
  expires_at 30 days after collection (YouTube API Services policy: refresh or delete stored data within 30 days).
The key is read from the environment (or the given .env file) and is never printed or written anywhere.
"""

import argparse
import json
import os
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

from common import ROOT, semantic_encoder  # first: puts backend/ on sys.path

# isort: split
import pandas as pd
import yaml

from audienceiq.data.youtube import QuotaExceededError, YouTubeClient
from audienceiq.data.youtube_adapter import comments_to_rows, videos_to_posts
from audienceiq.services.datasets import build_observed


def load_key(env_file: str | None) -> str:
    key = os.environ.get("YOUTUBE_API_KEY", "")
    if not key and env_file:
        for line in Path(env_file).read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("YOUTUBE_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not key:
        sys.exit("YOUTUBE_API_KEY is not set (environment or --env-file). Nothing was collected.")
    return key


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--months", type=int, default=24)
    ap.add_argument("--env-file", default=None)
    ap.add_argument("--max-comments", type=int, default=100)
    ap.add_argument("--model", default="mpnet")
    ap.add_argument("--no-semantic", action="store_true")
    args = ap.parse_args()

    client = YouTubeClient(load_key(args.env_file))
    snapshot = datetime.now(UTC).replace(microsecond=0)
    cutoff = snapshot - timedelta(days=round(args.months * 30.44))
    cfg = yaml.safe_load((ROOT / "config" / "youtube_channels.yaml").read_text(encoding="utf-8"))["brands"]
    tags = yaml.safe_load((ROOT / "config" / "campaign_tags.yaml").read_text(encoding="utf-8"))["campaign_tags"]
    brand_by_channel = {b["channel_id"]: b["display_name"] for b in cfg}
    t0 = time.time()
    try:
        channels = client.get_channels(list(brand_by_channel))
        uploads = {c["id"]: c["contentDetails"]["relatedPlaylists"]["uploads"] for c in channels}
        video_ids: list[str] = []
        for ch, pl in uploads.items():
            ids = list(client.iter_upload_video_ids(pl, cutoff))
            print(f"{brand_by_channel[ch]}: {len(ids)} videos since {cutoff.date()}", flush=True)
            video_ids += ids
        videos = client.get_videos(list(dict.fromkeys(video_ids)))
        posts = videos_to_posts(videos, brand_by_channel, snapshot, tags)
        raw_comments = []
        for v in videos:
            if int(v.get("statistics", {}).get("commentCount", 0) or 0) > 0:
                raw_comments += client.get_comments(v["id"], max_comments=args.max_comments)
    except QuotaExceededError as exc:
        sys.exit(f"Stopped: {exc}. Nothing was written.")
    comments = comments_to_rows(raw_comments)
    comments = comments[comments["comment_text"].str.strip() != ""]
    print(json.dumps({"videos": len(posts), "comments": len(comments), "quota_units": client.quota_used,
                      "seconds": round(time.time() - t0, 1)}), flush=True)

    private = ROOT / "data" / "observed" / "private" / snapshot.strftime("%Y-%m-%d")
    private.mkdir(parents=True, exist_ok=True)
    posts.to_csv(private / "posts.csv", index=False)
    comments.to_csv(private / "comments.csv", index=False)       # contains text: git-ignored, never deployed
    (private / "README.txt").write_text("PRIVATE raw YouTube API data (contains comment text). Never commit or share. "
                                        f"Delete after {(snapshot + timedelta(days=30)).date()} (30-day policy).\n",
                                        encoding="utf-8")
    encoder, model = (None, "")
    if not args.no_semantic:
        encoder, model = semantic_encoder(args.model)
    out = ROOT / "data" / "datasets"
    for old in out.glob("observed-youtube-*"):
        if old.is_dir():
            import shutil
            shutil.rmtree(old)
    result = build_observed(posts, comments, snapshot, client.quota_used, sorted(brand_by_channel.values()),
                            semantic_encoder=encoder, semantic_model=model, out_dir=out)
    ev = result["evaluation"]
    print(json.dumps({"dataset": result["dataset"]["dataset_id"], "posts": result["dataset"]["post_count"],
                      "comments": result["dataset"]["comment_count"], "selected": ev["clustering"]["selected_key"],
                      "flags": ev["anomalies"]["posts_flagged"], "recommendations": len(result["tables"]["recommendations"])},
                     indent=2))
    pd.DataFrame()  # keep pandas import used for type clarity


if __name__ == "__main__":
    main()
