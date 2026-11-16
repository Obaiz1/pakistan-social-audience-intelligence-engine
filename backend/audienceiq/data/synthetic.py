"""Deterministic SYNTHETIC classroom corpus: women's lawn-suit social posts + multilingual comments.

SYNTHETIC DEMO — NOT REAL SOCIAL MEDIA OBSERVATIONS. Brands are fictional ("Brand A"–"Brand F"); no real
brand name is ever attached to generated metrics. The generator simulates *brand-owned analytics exports*
(so shares/views exist only where such an export would plausibly contain them) and leaves metrics null
where a platform would not report them. Latent structure (need mixes by content/campaign/brand) and a
small number of injected anomalies exist so that the analytics have something real to discover; the
injected ground truth is returned separately and is used only for evaluation, never by the detectors.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

import numpy as np
import pandas as pd

from audienceiq.data.synthetic_text import make_comment

GENERATOR_VERSION = "synthetic-lawn-v1.0"
DEFAULT_SEED = 42
SNAPSHOT_AT = datetime(2026, 11, 14, tzinfo=UTC)
WINDOW_START = datetime(2025, 11, 15, tzinfo=UTC)
CATEGORY = "Women's lawn suits"

BRANDS = {
    #          scale  platform weights (IG, TT, FB, YT)   comment-need multipliers (the brand's "story")
    "Brand A": (1.00, (0.45, 0.20, 0.25, 0.10), {}),
    "Brand B": (0.80, (0.30, 0.45, 0.15, 0.10), {"discount": 1.5, "compliment": 1.1}),
    "Brand C": (0.60, (0.40, 0.20, 0.35, 0.05), {"delivery": 1.8, "order_issue": 2.6}),
    "Brand D": (0.50, (0.50, 0.10, 0.20, 0.20), {"price": 1.7, "fabric_quality": 1.2}),
    "Brand E": (0.45, (0.40, 0.25, 0.30, 0.05), {"size_fit": 2.3}),
    "Brand F": (0.25, (0.45, 0.25, 0.30, 0.00), {"availability": 2.1}),
}
PLATFORMS = ("Instagram", "TikTok", "Facebook", "YouTube")
CONTENT_MIX = {
    "Instagram": {"reel": .32, "product_photo": .30, "influencer_post": .16, "styling_video": .12, "sale_announcement": .10},
    "TikTok": {"styling_video": .36, "influencer_post": .30, "video": .22, "sale_announcement": .12},
    "Facebook": {"product_photo": .42, "video": .22, "sale_announcement": .20, "influencer_post": .16},
    "YouTube": {"video": .55, "styling_video": .45},
}

CAMPAIGNS = [
    # id, name, type, start, end, view multiplier, comment-need multipliers
    ("C-WINTER", "Winter Collection", "seasonal", date(2025, 11, 15), date(2026, 1, 31), 1.00, {"fabric_quality": 1.3}),
    ("C-BFRIDAY", "Black Friday Sale", "sale", date(2025, 11, 24), date(2025, 11, 30), 1.25,
     {"discount": 2.2, "delivery": 1.4, "order_issue": 1.5}),
    ("C-1212", "12.12 Sale", "sale", date(2025, 12, 8), date(2025, 12, 14), 1.35,
     {"discount": 2.2, "delivery": 1.6, "order_issue": 1.8}),
    ("C-LAWN1", "Spring/Summer Lawn Launch", "launch", date(2026, 2, 10), date(2026, 3, 31), 1.20,
     {"price": 1.3, "fabric_quality": 1.3, "availability": 1.2}),
    ("C-RAMADAN", "Ramadan Edit", "festive", date(2026, 2, 18), date(2026, 3, 4), 1.10, {"availability": 1.2}),
    ("C-EIDFITR", "Eid ul Fitr Collection", "festive", date(2026, 3, 5), date(2026, 3, 22), 1.50,
     {"availability": 1.8, "delivery": 1.7, "size_fit": 1.2}),
    ("C-LAWN2", "Summer Lawn Vol. 2", "launch", date(2026, 4, 15), date(2026, 6, 30), 1.15, {"price": 1.2}),
    ("C-EIDADHA", "Eid ul Adha Collection", "festive", date(2026, 5, 12), date(2026, 5, 28), 1.30,
     {"availability": 1.6, "delivery": 1.5}),
    ("C-MIDSALE", "Mid-Season Sale", "sale", date(2026, 7, 1), date(2026, 7, 20), 1.15, {"discount": 2.0, "delivery": 1.3}),
    ("C-PREEID", "Pre-Eid Flash Sale", "sale", date(2026, 3, 13), date(2026, 3, 18), 1.30,
     {"discount": 2.0, "delivery": 2.0, "availability": 1.5}),
    ("C-AZADI", "Azadi Collection", "festive", date(2026, 8, 1), date(2026, 8, 14), 1.10, {"compliment": 1.2}),
    ("C-AZADISALE", "Independence Day Sale", "sale", date(2026, 8, 10), date(2026, 8, 14), 1.20, {"discount": 2.0}),
    ("C-WEDDING", "Wedding & Festive Formals", "festive", date(2026, 9, 15), date(2026, 10, 31), 1.15,
     {"fabric_quality": 1.4, "price": 1.3}),
    ("C-1111", "11.11 Sale", "sale", date(2026, 11, 6), date(2026, 11, 12), 1.35,
     {"discount": 2.4, "delivery": 1.6, "order_issue": 1.6}),
]
EVERGREEN = ("C-NONE", "No campaign (evergreen)", "none", None, None, 0.90, {})

BASE_NEEDS = {"compliment": .22, "price": .14, "purchase_inquiry": .10, "availability": .10, "size_fit": .08,
              "delivery": .08, "discount": .06, "fabric_quality": .08, "order_issue": .05, "other": .09}
CONTENT_NEEDS = {
    "sale_announcement": {"discount": 3.5, "delivery": 1.3, "compliment": 0.5},
    "product_photo": {"price": 1.7, "availability": 1.5, "size_fit": 1.3},
    "styling_video": {"compliment": 1.6, "fabric_quality": 1.5, "size_fit": 1.2},
    "influencer_post": {"compliment": 1.5, "purchase_inquiry": 1.3, "price": 1.2, "other": 1.3},
    "reel": {"compliment": 1.25},
    "video": {"other": 1.2},
}
PLATFORM_NEEDS = {"TikTok": {"compliment": 1.2, "other": 1.3}, "Facebook": {"price": 1.2, "delivery": 1.2, "purchase_inquiry": 1.4}}
LANG_BASE = {"english": .33, "roman_urdu": .45, "urdu": .14, "mixed": .08}
LANG_PLATFORM = {"Facebook": {"urdu": 1.6}, "TikTok": {"roman_urdu": 1.25}, "YouTube": {"english": 1.15}}

# Platform engagement profile: median 'reach' at brand scale 1, likes/reach, comments/reach, shares/reach, age tau (days)
PLATFORM_PROFILE = {
    "Instagram": (30_000, 0.045, 0.0030, 0.0040, 2.0),
    "TikTok": (55_000, 0.060, 0.0020, 0.0080, 3.0),
    "Facebook": (16_000, 0.022, 0.0040, 0.0030, 2.5),
    "YouTube": (11_000, 0.014, 0.0015, None, 6.0),
}
CONTENT_EFFECT = {  # (reach multiplier, like-rate multiplier, comment-rate multiplier, share multiplier)
    "reel": (1.30, 1.10, 1.00, 1.10),
    "video": (1.00, 1.00, 1.00, 1.00),
    "product_photo": (0.70, 0.90, 1.40, 0.70),
    "influencer_post": (1.60, 1.15, 1.20, 1.20),
    "styling_video": (1.20, 1.28, 1.05, 1.45),
    "sale_announcement": (0.90, 0.75, 1.80, 1.30),
}
ANOMALY_TYPES = {  # type: (count, description)
    "viral_spike": (36, "reach ×6–12 and like-rate ×1.6 (e.g. an influencer repost going viral)"),
    "engagement_collapse": (24, "reach ×3–5 but like-rate ×0.15 (e.g. boosted views that did not engage)"),
    "comment_surge": (20, "comments ×5–8 dominated by order complaints and delivery questions"),
    "giveaway_comments": (14, "comments ×6–10 dominated by giveaway tags ('Done @friend')"),
}


@dataclass
class SyntheticCorpus:
    posts: pd.DataFrame
    comments: pd.DataFrame
    campaigns: pd.DataFrame
    truth_posts: pd.DataFrame
    truth_comments: pd.DataFrame
    seed: int
    snapshot_at: datetime


def _norm(weights: dict[str, float]) -> tuple[list[str], np.ndarray]:
    keys = list(weights)
    p = np.array([weights[k] for k in keys], dtype=float)
    return keys, p / p.sum()


def _apply(base: dict[str, float], *mods: dict[str, float]) -> dict[str, float]:
    out = dict(base)
    for m in mods:
        for k, v in m.items():
            if k in out:
                out[k] *= v
    return out


def _campaign_for(rng: np.random.Generator, day: date, content_type: str):
    active = [c for c in CAMPAIGNS if c[3] <= day <= c[4]]
    if content_type == "sale_announcement":
        sales = [c for c in active if c[2] == "sale"]
        return sales[int(rng.integers(len(sales)))] if sales else None
    non_sale = [c for c in active if c[2] != "sale"]
    sales = [c for c in active if c[2] == "sale"]
    if sales and rng.random() < 0.55:
        return sales[int(rng.integers(len(sales)))]
    if non_sale and rng.random() < 0.80:
        # the more specific (shorter) campaign wins more often
        lengths = np.array([(c[4] - c[3]).days + 1 for c in non_sale], dtype=float)
        p = (1 / lengths) / (1 / lengths).sum()
        return non_sale[int(rng.choice(len(non_sale), p=p))]
    return EVERGREEN


def _sample_dates(rng: np.random.Generator, n: int) -> list[datetime]:
    days = (SNAPSHOT_AT - WINDOW_START).days
    weights = np.ones(days)
    for c in CAMPAIGNS:
        s, e = (c[3] - WINDOW_START.date()).days, (c[4] - WINDOW_START.date()).days
        weights[max(s, 0):min(e + 1, days)] *= {"sale": 3.5, "festive": 2.2}.get(c[2], 1.4)
    weights /= weights.sum()
    day_idx = rng.choice(days, size=n, p=weights)
    # posting hour skewed to Pakistani evening (PKT = UTC+5): 12:00–18:00 UTC is 17:00–23:00 PKT
    hours = rng.choice(24, size=n, p=_hour_profile())
    minutes = rng.integers(0, 60, size=n)
    return [WINDOW_START + timedelta(days=int(d), hours=int(h), minutes=int(m)) for d, h, m in zip(day_idx, hours, minutes,
                                                                                                    strict=True)]


def _hour_profile() -> np.ndarray:
    p = np.full(24, 0.5)
    p[4:8] = 1.0
    p[8:12] = 1.5
    p[12:18] = 3.0
    p[18:20] = 1.2
    return p / p.sum()


def generate(n_posts: int = 3000, seed: int = DEFAULT_SEED) -> SyntheticCorpus:
    """Generate the corpus. Same (n_posts, seed) → identical output."""
    if not 50 <= n_posts <= 10_000:
        raise ValueError("n_posts must be between 50 and 10,000")
    rng = np.random.default_rng(seed)
    brand_names = list(BRANDS)
    brand_p = np.array([BRANDS[b][0] ** 0.5 for b in brand_names])
    brand_p /= brand_p.sum()
    dates = sorted(_sample_dates(rng, n_posts))

    rows, truth_rows = [], []
    for i, published in enumerate(dates):
        brand = brand_names[int(rng.choice(len(brand_names), p=brand_p))]
        scale, pw, _ = BRANDS[brand]
        platform = PLATFORMS[int(rng.choice(4, p=np.array(pw) / sum(pw)))]
        day = published.date()
        mix = dict(CONTENT_MIX[platform])
        if not any(c[2] == "sale" and c[3] <= day <= c[4] for c in CAMPAIGNS):
            mix.pop("sale_announcement", None)
        elif "sale_announcement" in mix:
            mix["sale_announcement"] *= 3.0          # sale windows are dominated by sale posts
        keys, p = _norm(mix)
        content_type = keys[int(rng.choice(len(keys), p=p))]
        camp = _campaign_for(rng, day, content_type) or EVERGREEN
        age_days = max(0, (SNAPSHOT_AT - published).days)
        reach0, like_r, com_r, share_r, tau = PLATFORM_PROFILE[platform]
        r_mult, l_mult, c_mult, s_mult = CONTENT_EFFECT[content_type]
        maturity = 1 - np.exp(-(SNAPSHOT_AT - published).total_seconds() / 86400 / tau)
        reach = reach0 * scale * r_mult * camp[5] * maturity * rng.lognormal(0, 0.55)
        festive_like = 1.12 if camp[2] == "festive" else 1.0
        lr = like_r * l_mult * festive_like * rng.lognormal(0, 0.30)
        cr = com_r * c_mult * rng.lognormal(0, 0.45)
        sr = None if share_r is None else share_r * s_mult * rng.lognormal(0, 0.45)
        rows.append({
            "i": i, "brand": brand, "platform": platform, "content_type": content_type, "campaign_id": camp[0],
            "campaign": camp[1], "published": published, "age": age_days, "reach": reach, "lr": lr, "cr": cr, "sr": sr,
        })
        truth_rows.append({"anomaly": None})

    # Inject anomalies into mature posts (≥ 10 days) chosen at random, recorded only in the truth table.
    mature = [r["i"] for r in rows if r["age"] >= 10]
    counts = {k: max(1, round(c * n_posts / 3000)) for k, (c, _) in ANOMALY_TYPES.items()}  # ~3.1% of posts
    chosen = rng.choice(mature, size=min(len(mature), sum(counts.values())), replace=False)
    cursor = 0
    for kind, count in counts.items():
        for idx in chosen[cursor:cursor + count]:
            r = rows[int(idx)]
            truth_rows[int(idx)]["anomaly"] = kind
            if kind == "viral_spike":
                r["reach"] *= rng.uniform(6, 12)
                r["lr"] *= 1.6
            elif kind == "engagement_collapse":
                r["reach"] *= rng.uniform(3, 5)
                r["lr"] *= 0.15
                r["cr"] *= 0.3
            elif kind == "comment_surge":
                r["cr"] *= rng.uniform(5, 8)
            elif kind == "giveaway_comments":
                r["cr"] *= rng.uniform(6, 10)
        cursor += count

    posts, truth_posts = [], []
    for r, t in zip(rows, truth_rows, strict=True):
        pid = f"SYN-P{r['i'] + 1:05d}"
        reach = max(1.0, r["reach"])
        likes = int(rng.poisson(reach * r["lr"]))
        comments_count = int(rng.poisson(reach * r["cr"]))
        shares = None if r["sr"] is None else int(rng.poisson(reach * r["sr"]))
        is_photo = r["content_type"] in {"product_photo", "sale_announcement"} or (
            r["content_type"] == "influencer_post" and r["platform"] in {"Instagram", "Facebook"} and rng.random() < 0.5)
        views = None if (is_photo and r["platform"] in {"Instagram", "Facebook"}) else int(round(reach))
        if r["platform"] == "Instagram" and rng.random() < 0.012:
            likes = None                                    # owner hid the like count: unknown, not zero
        posts.append({
            "post_id": pid, "source_post_id": pid, "brand": r["brand"], "platform": r["platform"],
            "campaign_id": r["campaign_id"], "campaign": r["campaign"], "content_type": r["content_type"],
            "content_type_raw": r["content_type"], "product_category": CATEGORY,
            "likes": likes, "comments_count": comments_count, "shares": shares, "views": views,
            "published_at": r["published"].isoformat().replace("+00:00", "Z"),
            "days_since_post": r["age"],
            "post_text": f"{r['campaign']} — {CATEGORY.lower()} ({r['content_type'].replace('_', ' ')}) [synthetic caption]",
        })
        truth_posts.append({"post_id": pid, "injected_anomaly": t["anomaly"] or ""})
    posts_df = pd.DataFrame(posts)

    comments, truth_comments = _generate_comments(rng, posts_df, {p["post_id"]: p["injected_anomaly"] for p in truth_posts})
    campaigns = pd.DataFrame([
        {"campaign_id": c[0], "name": c[1], "campaign_type": c[2],
         "start_date": c[3].isoformat() if c[3] else None, "end_date": c[4].isoformat() if c[4] else None,
         "campaign_source": "synthetic_calendar"} for c in [*CAMPAIGNS, EVERGREEN]])
    return SyntheticCorpus(posts_df, comments, campaigns, pd.DataFrame(truth_posts), truth_comments, seed, SNAPSHOT_AT)


def _generate_comments(rng: np.random.Generator, posts: pd.DataFrame, anomalies: dict[str, str]):
    camp_needs = {c[0]: c[6] for c in [*CAMPAIGNS, EVERGREEN]}
    rows, truth = [], []
    n = 0
    for p in posts.itertuples(index=False):
        total = int(p.comments_count or 0)
        if total == 0:
            continue
        # A brand export / API page keeps only part of the thread: retained ≤ platform total.
        retained = int(min(total, round(np.sqrt(total) * 1.1) + 1, 30))
        kind = anomalies.get(p.post_id, "")
        needs = _apply(BASE_NEEDS, CONTENT_NEEDS.get(p.content_type, {}), PLATFORM_NEEDS.get(p.platform, {}),
                       camp_needs.get(p.campaign_id, {}), BRANDS[p.brand][2])
        if kind == "comment_surge":
            needs = _apply(needs, {"order_issue": 7.0, "delivery": 3.0})
        if kind == "giveaway_comments":
            needs = dict(needs, giveaway=sum(needs.values()) * 4)
        need_keys, need_p = _norm(needs)
        lang_keys, lang_p = _norm(_apply(LANG_BASE, LANG_PLATFORM.get(p.platform, {})))
        published = datetime.fromisoformat(p.published_at.replace("Z", "+00:00"))
        for _ in range(retained):
            n += 1
            need = need_keys[int(rng.choice(len(need_keys), p=need_p))]
            language = lang_keys[int(rng.choice(len(lang_keys), p=lang_p))]
            text, secondary, template = make_comment(rng, need, language)
            delay_h = float(rng.exponential(30))
            ts = min(published + timedelta(hours=delay_h), SNAPSHOT_AT - timedelta(minutes=1))
            cid = f"SYN-C{n:06d}"
            rows.append({"comment_id": cid, "post_id": p.post_id, "comment_text": text,
                         "published_at": ts.isoformat().replace("+00:00", "Z"),
                         "like_count": int(rng.geometric(0.55)) - 1})
            truth.append({"comment_id": cid, "true_need": "other" if need == "giveaway" else need,
                          "generator_need": need, "secondary_need": secondary or "", "true_language": language,
                          "template_index": template})
    return pd.DataFrame(rows), pd.DataFrame(truth)
