"""Evidence-linked marketing recommendations (Q5). Deterministic; no LLM is needed or used by default.

A card is emitted only when its evidence clears explicit gates; otherwise nothing is asserted:
- need cards: discovered clusters whose post-hoc name has agreement >= MIN_AGREEMENT, support >= MIN_SUPPORT comments
  and share >= MIN_SHARE of clustered comments;
- concentration cards: a need over-represented in a campaign / brand / platform / content type (lift >= MIN_LIFT,
  >= MIN_GROUP_COMMENTS comments, two-proportion z-test, Benjamini–Hochberg adjusted p < ALPHA);
- content cards: Repo A rule — significant (BH p < 0.05) attention-index difference with effect size >= small;
- investigation cards: recurring anomaly flags (>= MIN_FLAGS) of one kind/direction.
Card anatomy adapted from Repo A src/recommendations/engine.py (@957e3b6): what / why / n / limitations / A-B test.
"""

import hashlib
import json
import math
from datetime import UTC, datetime

import numpy as np
import pandas as pd
from scipy import stats

from audienceiq.analytics.stats import benjamini_hochberg
from audienceiq.constants import CONTENT_TYPE_LABELS, NEED_LABELS

MIN_AGREEMENT = 0.5
MIN_SUPPORT = 30
MIN_SHARE = 0.04
MIN_LIFT = 1.5
MIN_GROUP_COMMENTS = 50
ALPHA = 0.05
MIN_FLAGS = 3
MAX_CONCENTRATION_CARDS = 8

NEED_ACTIONS = {
    "price": ("customer_service", "Answer price questions before they are asked",
              "Put the PKR price (stitched/unstitched) in the caption, first frame or a pinned comment of new product posts, "
              "and set a DM/WhatsApp quick reply with the current price list.",
              "For 2 weeks, alternate comparable product posts with and without the price in the caption. Compare the share "
              "of comments in the price cluster (expect lower) and purchase-inquiry comments (expect equal or higher)."),
    "discount": ("promotion", "Make current offers easy to find",
                 "Publish a pinned 'current offers' highlight/post and state sale dates and eligibility (stitched, unstitched, "
                 "minimum order) in sale-period captions; test sale messaging only where discount demand is evidenced.",
                 "Run sale-period captions in two versions (explicit '% off + end date' vs generic 'sale live') on comparable "
                 "posts for one sale window; compare discount-question share and purchase inquiries per 1,000 views."),
    "delivery": ("customer_service", "Publish delivery times and charges by city",
                 "Add a delivery-time and charges table by city to highlights and captions, state Eid/sale order cut-off dates, "
                 "and prepare a DM macro so delivery questions are answered within hours.",
                 "Add delivery details to half of the next 20 posts (alternating). Compare the delivery-question share and the "
                 "time-to-first-reply on delivery comments between the two halves."),
    "availability": ("customer_service", "Show stock and size availability up front",
                     "Use 'available sizes / in stock' stickers or caption lines, announce restocks, and link a store/outlet "
                     "locator so availability questions get an answer without a DM.",
                     "For 2 weeks, add availability lines to alternate posts of new articles and compare the availability-cluster "
                     "share and 'sold out' complaints between versions."),
    "size_fit": ("content", "Publish a size guide and model measurements",
                 "Add a size-chart carousel slide and the model's height/size to captions, and pin a size-guide link on "
                 "styling and product posts.",
                 "Include the size-guide slide on alternate product posts for 3 weeks; compare size-question share and later "
                 "wrong-size complaints."),
    "fabric_quality": ("content", "Show the fabric, not just the look",
                       "Create fabric close-up and wash/colour-fastness content and state fabric composition (lawn count, "
                       "chiffon/silk dupatta) in captions.",
                       "Post fabric close-ups for half of a new collection's articles; compare fabric-question share and "
                       "engagement (attention index) with the other half."),
    "purchase_inquiry": ("customer_service", "Turn 'inbox/details' comments into orders faster",
                         "Route 'price inbox / details / how to order' comments to an automated DM or WhatsApp reply with the "
                         "order link and price; track response time and conversion of those threads.",
                         "Enable the auto-reply for alternate days over 2 weeks; compare reply time and the number of inquiry "
                         "threads that reach an order link."),
    "order_issue": ("customer_service", "Escalate order complaints quickly and fix the root cause",
                    "Escalate public order complaints to support within 24 hours with a standard public reply, publish "
                    "order-tracking steps, and review courier/dispatch performance where complaints concentrate.",
                    "Introduce the 24-hour escalation for one brand/platform first; compare repeat complaints and complaint "
                    "share over the next 4 weeks against the rest."),
    "compliment": ("content", "Reuse what the audience praises",
                   "Reshare praised looks and customer photos (with permission) and feature the most-praised designs/colours "
                   "in the next campaign's hero content.",
                   "Feature praised designs in half of the next campaign's hero posts; compare attention index vs the other half."),
}
BASE_LIMITATIONS = [
    "Associational, not causal: campaigns, budgets and seasons are confounded with content and timing.",
    "Comments are a retained sample of visible threads, not every comment a post received.",
    "Clusters were discovered without labels; their names come from a rule-based reference labeller (agreement shown).",
]


def _rid(*parts) -> str:
    return "REC-" + hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:8].upper()


def _strength(n: int, agreement: float | None = None, p: float | None = None) -> str:
    if (p is not None and p < 0.001 and n >= 100) or (n >= 200 and (agreement or 0) >= 0.7):
        return "strong"
    if n >= MIN_GROUP_COMMENTS:
        return "moderate"
    return "limited"


def _card(**kw) -> dict:
    kw.setdefault("limitations", [])
    kw["limitations"] = kw["limitations"] + BASE_LIMITATIONS + kw.pop("extra_limitations", [])
    return kw


def need_cards(profiles: list[dict], n_clustered: int) -> list[dict]:
    by_need: dict[str, list[dict]] = {}
    for p in profiles:
        if p["cluster_id"] == -1 or p["need_category"] in {"mixed", "other", "noise"}:
            continue
        if p["label_agreement"] >= MIN_AGREEMENT:
            by_need.setdefault(p["need_category"], []).append(p)
    cards = []
    for need, clusters in by_need.items():
        size = sum(c["size"] for c in clusters)
        share = size / n_clustered if n_clustered else 0
        if size < MIN_SUPPORT or share < MIN_SHARE or need not in NEED_ACTIONS:
            continue
        agreement = sum(c["label_agreement"] * c["size"] for c in clusters) / size
        action_type, title, what, test = NEED_ACTIONS[need]
        label = NEED_LABELS[need]
        ids = ", ".join(f"#{c['cluster_id']}" for c in clusters)
        priority = 1 if (share >= 0.10 and need != "compliment") else 3 if need == "compliment" else 2
        cards.append(_card(
            recommendation_id=_rid("need", need), action_type=action_type, title=title, what_to_do=what,
            why_it_matters=(f"{size:,} comments ({share:.1%} of {n_clustered:,} clustered comments) fall in discovered "
                            f"cluster(s) {ids} named '{label}' (name agreement {agreement:.0%})."),
            audience_need=need, where={"scope": "all posts in the selected dataset"},
            linked_evidence=[{"type": "cluster", "id": c["cluster_id"], "label": c["label"], "size": c["size"]}
                             for c in clusters],
            priority=priority, evidence_strength=_strength(size, agreement), sample_size=size,
            metrics={"comments": size, "share_of_clustered": round(share, 4), "name_agreement": round(agreement, 4),
                     "denominator": "clustered (non-noise) comments"},
            test_plan=test))
    return cards


def concentration_cards(cn: pd.DataFrame, need_set: set[str]) -> list[dict]:
    """cn: clustered comments with columns need, campaign, brand, platform, content_type."""
    if cn is None or cn.empty:
        return []
    c = cn[~cn["need"].isin(["noise", "mixed", "other"])]
    total = len(c)
    tests = []
    for dim in ("campaign", "brand", "platform", "content_type"):
        for val, g in c.groupby(dim):
            n_in = len(g)
            n_out = total - n_in
            if n_in < MIN_GROUP_COMMENTS or n_out < MIN_GROUP_COMMENTS:
                continue
            for need in need_set:
                k_in = int((g["need"] == need).sum())
                k_out = int((c["need"] == need).sum()) - k_in
                p_in, p_out = k_in / n_in, k_out / n_out
                if p_out == 0 or k_in < 15:
                    continue
                lift = p_in / p_out
                pooled = (k_in + k_out) / total
                se = math.sqrt(pooled * (1 - pooled) * (1 / n_in + 1 / n_out))
                z = (p_in - p_out) / se if se else 0
                tests.append({"dim": dim, "value": val, "need": need, "k": k_in, "n": n_in, "share": p_in,
                              "rest_share": p_out, "lift": lift, "z": z, "p": float(stats.norm.sf(z))})
    if not tests:
        return []
    t = pd.DataFrame(tests)
    t["p_adj"] = benjamini_hochberg(t["p"])
    t = t[(t["p_adj"] < ALPHA) & (t["lift"] >= MIN_LIFT)].sort_values(["lift", "z"], ascending=False)
    cards, used = [], set()
    for r in t.itertuples(index=False):
        if (r.need, r.dim) in used or len(cards) >= MAX_CONCENTRATION_CARDS:
            continue
        used.add((r.need, r.dim))
        action_type, title, what, test = NEED_ACTIONS.get(r.need, ("campaign_test", "", "", ""))
        label = NEED_LABELS[r.need]
        where_txt = CONTENT_TYPE_LABELS.get(r.value, r.value) if r.dim == "content_type" else r.value
        prefix = {"campaign": "During", "brand": "For", "platform": "On", "content_type": "On"}[r.dim]
        cards.append(_card(
            recommendation_id=_rid("conc", r.need, r.dim, r.value),
            action_type="campaign_test" if r.dim == "campaign" else action_type,
            title=f"{prefix} {where_txt}: address '{label}' first",
            what_to_do=f"{prefix} {where_txt}: {what[0].lower() + what[1:]}",
            why_it_matters=(f"{r.k:,} of {r.n:,} clustered comments ({r.share:.1%}) {('during' if r.dim == 'campaign' else 'for')} "
                            f"{where_txt} are in the '{label}' need vs {r.rest_share:.1%} elsewhere — {r.lift:.1f}× more common "
                            f"(two-proportion z = {r.z:.1f}, BH-adjusted p = {r.p_adj:.1e})."),
            audience_need=r.need, where={r.dim: r.value},
            linked_evidence=[{"type": "need_concentration", "dimension": r.dim, "value": r.value, "need": r.need,
                              "lift": round(r.lift, 3)}],
            priority=1 if r.lift >= 2 and r.n >= 100 else 2,
            evidence_strength=_strength(r.n, p=r.p_adj), sample_size=int(r.n),
            metrics={"share": round(r.share, 4), "rest_share": round(r.rest_share, 4), "lift": round(r.lift, 3),
                     "z": round(r.z, 2), "p_adj": float(f"{r.p_adj:.3g}"), "comments_in_group": int(r.n)},
            test_plan=test,
            extra_limitations=["Lift compares this group with all other clustered comments; other differences between "
                               "the groups (platform mix, timing) may contribute."]))
    return cards


def content_cards(content_comparison: dict) -> list[dict]:
    cards = []
    for r in content_comparison.get("rows", []):
        if not r.get("significant") or r.get("effect") not in {"small", "medium", "large"}:
            continue
        up = (r["cliffs_delta"] or 0) > 0
        label = r["label"]
        cards.append(_card(
            recommendation_id=_rid("content", r["group"]), action_type="content",
            title=("Test more " if up else "Rethink ") + f"{label.lower()} posts",
            what_to_do=(f"Increase the share of {label.lower()} posts in the next content calendar and test them against "
                        "your usual formats." if up else
                        f"Do not add more {label.lower()} posts without a change; test a new treatment against the current one."),
            why_it_matters=(f"Mature {label.lower()} posts have median attention index {r['median']:.2f} (95% CI "
                            f"{r['ci_low']:.2f}–{r['ci_high']:.2f}) vs {r['rest_median']:.2f} for all other posts (1.00 = the "
                            f"brand's typical post on that platform); Cliff's δ {r['cliffs_delta']:+.2f} ({r['effect']}), "
                            f"BH-adjusted p = {r['p_adj']:.3f}, n = {r['n']}."),
            audience_need=None, where={"content_type": r["group"]},
            linked_evidence=[{"type": "content_comparison", "dimension": "content_type", "group": r["group"]}],
            priority=1 if r["effect"] in {"medium", "large"} else 2,
            evidence_strength={"large": "strong", "medium": "moderate"}.get(r["effect"], "limited"),
            sample_size=int(r["n"]),
            metrics={k: r[k] for k in ("median", "rest_median", "ci_low", "ci_high", "cliffs_delta", "p_adj", "n")},
            test_plan=(f"Publish 10–20 {label.lower()} posts and 10–20 otherwise-similar posts in the same weeks, brands and "
                       "platforms. Compare median attention index after 7 days; keep paid boosting equal or exclude boosted posts."),
            extra_limitations=([f"Effect size is {r['effect']}: expect a modest or uncertain lift."]
                               if r["effect"] == "small" else [])))
    return cards


def anomaly_cards(flags: pd.DataFrame, posts: pd.DataFrame) -> list[dict]:
    if flags is None or flags.empty:
        return []
    f = flags.merge(posts[["post_id", "content_type", "campaign", "brand", "platform"]], on="post_id", how="left")
    cards = []
    specs = [
        ("engagement", "positive", "investigation", "Study the unusually high-performing posts before repeating them",
         "Review the {n} posts flagged far above their peer cohort: check for influencer reposts, paid boosts or giveaways, "
         "and document what (creative, timing, collaborator) is repeatable.",
         "Pick 2–3 repeatable elements from the flagged posts and test them on new posts vs a control; compare attention index."),
        ("engagement", "negative", "investigation", "Check high-reach posts that failed to engage",
         "Review the {n} posts flagged far below their peer cohort: confirm whether views were paid/boosted, and pause "
         "boosting creatives that do not engage.",
         "For the next boosted posts, track engagement rate separately for paid and organic views and compare with this baseline."),
        ("need_mix", "positive", "customer_service", "Respond to posts whose comments turned into complaint or question storms",
         "Open the {n} posts whose comment mix differs sharply from comparable posts and reply to the over-represented need "
         "(often order problems or delivery questions) publicly and via DM.",
         "Measure reply time and the complaint share on these posts before and after a public response."),
        ("comment_pattern", "positive", "customer_service", "Clear unanswered questions on comment-heavy posts",
         "Check the {n} posts with unusually many comments per like for unanswered questions, complaints or giveaway "
         "spam; answer or moderate them.",
         "Track the share of comment-heavy posts with a brand reply within 24 hours over the next month."),
    ]
    for kind, direction, action_type, title, what, test in specs:
        sub = f[(f["kind"] == kind) & (f["direction"] == direction)]
        if len(sub) < MIN_FLAGS:
            continue
        top_ct = sub["content_type"].value_counts()
        top_camp = sub["campaign"].value_counts()
        cards.append(_card(
            recommendation_id=_rid("anom", kind, direction), action_type=action_type, title=title,
            what_to_do=what.format(n=len(sub)),
            why_it_matters=(f"{len(sub)} statistically unusual posts ({kind.replace('_', ' ')}, {direction}) were flagged against "
                            f"comparable peer cohorts; most common content type: "
                            f"{CONTENT_TYPE_LABELS.get(top_ct.index[0], top_ct.index[0])} ({top_ct.iloc[0]}), campaign: "
                            f"{top_camp.index[0]} ({top_camp.iloc[0]})."),
            audience_need=None, where={"content_type": top_ct.index[0]},
            linked_evidence=[{"type": "anomaly", "id": fid, "post_id": pid}
                             for fid, pid in zip(sub["flag_id"].head(12), sub["post_id"].head(12), strict=True)],
            priority=1 if kind == "need_mix" else 2, evidence_strength="moderate" if len(sub) >= 10 else "limited",
            sample_size=int(len(sub)),
            metrics={"flags": int(len(sub)), "median_score": round(float(np.median(sub["score"])), 3)},
            test_plan=test,
            extra_limitations=["Anomalies are statistical outliers vs comparable posts, not proof of fraud or bot activity."]))
    return cards


def build_recommendations(profiles: list[dict], n_clustered: int, clustered_comments: pd.DataFrame,
                          content_comparison: dict, flags: pd.DataFrame, posts: pd.DataFrame, dataset_id: str,
                          mode: str) -> list[dict]:
    actionable = {p["need_category"] for p in profiles
                  if p["cluster_id"] != -1 and p["label_agreement"] >= MIN_AGREEMENT and p["need_category"] in NEED_ACTIONS}
    cards = (need_cards(profiles, n_clustered) + concentration_cards(clustered_comments, actionable)
             + content_cards(content_comparison) + anomaly_cards(flags, posts))
    now = datetime.now(UTC).isoformat(timespec="seconds")
    extra = ["SYNTHETIC DEMO data: these cards demonstrate the method; they are not findings about real brands."] \
        if mode == "synthetic" else []
    cards.sort(key=lambda c: (c["priority"], {"strong": 0, "moderate": 1, "limited": 2}[c["evidence_strength"]],
                              -c["sample_size"]))
    for c in cards:
        c["limitations"] = extra + c["limitations"]
        c["dataset_id"], c["generated_at"] = dataset_id, now
    return cards


def to_rows(cards: list[dict]) -> pd.DataFrame:
    return pd.DataFrame([{
        "recommendation_id": c["recommendation_id"], "dataset_id": c["dataset_id"], "generated_at": c["generated_at"],
        "action_type": c["action_type"], "title": c["title"], "what_to_do": c["what_to_do"],
        "why_it_matters": c["why_it_matters"], "audience_need": c["audience_need"],
        "where_json": json.dumps(c["where"], ensure_ascii=False),
        "linked_evidence_json": json.dumps(c["linked_evidence"], ensure_ascii=False, default=str),
        "priority": c["priority"], "evidence_strength": c["evidence_strength"], "sample_size": c["sample_size"],
        "metrics_json": json.dumps(c["metrics"], default=float), "limitations_json": json.dumps(c["limitations"]),
        "test_plan": c["test_plan"]} for c in cards])
