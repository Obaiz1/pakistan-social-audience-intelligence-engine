import numpy as np
import pandas as pd

from audienceiq.recommendations.engine import (
    build_recommendations,
    concentration_cards,
    content_cards,
    need_cards,
    to_rows,
)


def _profile(cid, need, size, agreement):
    return {"cluster_id": cid, "label": need, "need_category": need, "label_agreement": agreement, "size": size}


def test_need_card_requires_support_share_and_agreement():
    good = need_cards([_profile(0, "delivery", 300, 0.9)], n_clustered=1000)
    assert len(good) == 1 and good[0]["audience_need"] == "delivery"
    assert good[0]["linked_evidence"][0] == {"type": "cluster", "id": 0, "label": "delivery", "size": 300}
    assert need_cards([_profile(0, "delivery", 20, 0.9)], 1000) == []          # too few comments
    assert need_cards([_profile(0, "delivery", 300, 0.3)], 1000) == []         # name not trustworthy
    assert need_cards([_profile(0, "delivery", 30, 0.9)], 10_000) == []        # share below threshold
    assert need_cards([_profile(0, "mixed", 900, 0.9)], 1000) == []            # mixed clusters never asserted
    assert need_cards([_profile(-1, "noise", 900, 0.0)], 1000) == []


def test_every_card_has_evidence_numbers_limitations_and_test():
    card = need_cards([_profile(0, "price", 400, 0.8), _profile(3, "price", 100, 0.7)], 1000)[0]
    assert card["sample_size"] == 500 and "50.0%" in card["why_it_matters"]
    assert card["test_plan"] and len(card["limitations"]) >= 3
    assert {e["id"] for e in card["linked_evidence"]} == {0, 3}


def test_concentration_card_needs_significant_lift():
    rng = np.random.default_rng(0)
    rows = []
    for camp, p_disc, n in (("11.11 Sale", 0.45, 300), ("Evergreen", 0.10, 900)):
        rows += [{"need": "discount" if rng.random() < p_disc else "price", "campaign": camp, "brand": "A",
                  "platform": "Instagram", "content_type": "reel"} for _ in range(n)]
    cards = concentration_cards(pd.DataFrame(rows), {"discount", "price"})
    assert any(c["where"] == {"campaign": "11.11 Sale"} and c["audience_need"] == "discount" for c in cards)
    flat = [{"need": "discount" if rng.random() < 0.2 else "price", "campaign": c, "brand": "A", "platform": "Instagram",
             "content_type": "reel"} for c in ("A", "B") for _ in range(400)]
    assert concentration_cards(pd.DataFrame(flat), {"discount", "price"}) == []   # no real difference → no card


def test_content_cards_only_from_significant_meaningful_effects():
    rows = [{"group": "styling_video", "label": "Styling video", "significant": True, "effect": "small", "cliffs_delta": 0.2,
             "median": 1.3, "rest_median": 1.0, "ci_low": 1.2, "ci_high": 1.4, "p_adj": 0.001, "n": 300},
            {"group": "reel", "label": "Reel", "significant": True, "effect": "negligible", "cliffs_delta": 0.05,
             "median": 1.02, "rest_median": 1.0, "ci_low": 1.0, "ci_high": 1.05, "p_adj": 0.01, "n": 300},
            {"group": "video", "label": "Video", "significant": False, "effect": "medium", "cliffs_delta": -0.4,
             "median": 0.7, "rest_median": 1.0, "ci_low": 0.5, "ci_high": 0.9, "p_adj": 0.2, "n": 30}]
    cards = content_cards({"rows": rows})
    assert [c["where"]["content_type"] for c in cards] == ["styling_video"]


def test_unsupported_inputs_emit_nothing():
    cards = build_recommendations([], 0, pd.DataFrame(), {"rows": []}, pd.DataFrame(), pd.DataFrame(), "d", "synthetic")
    assert cards == []


def test_rows_serialise():
    cards = build_recommendations([_profile(0, "delivery", 300, 0.9)], 1000, pd.DataFrame(), {"rows": []}, pd.DataFrame(),
                                  pd.DataFrame(), "d", "synthetic")
    df = to_rows(cards)
    assert df.loc[0, "priority"] in (1, 2, 3) and "SYNTHETIC" in df.loc[0, "limitations_json"]


class _Resp:
    def __init__(self, text):
        self._t = text

    def raise_for_status(self):
        return None

    def json(self):
        return {"choices": [{"message": {"content": self._t}}]}


CARD = {"title": "Answer price questions", "what_to_do": "Put the price in captions.",
        "why_it_matters": "5,884 comments (17.4% of 33,776) are price questions (agreement 72%).",
        "sample_size": 5884, "evidence_strength": "strong", "test_plan": "Alternate for 2 weeks."}


def test_llm_wording_is_optional_and_number_locked():
    from audienceiq.recommendations.wording import number_lock_ok, rewrite

    assert rewrite(CARD, api_key="")["used_llm"] is False                     # no key → deterministic text
    ok = rewrite(CARD, api_key="k", post=lambda *a, **k: _Resp("About 17.4% of comments ask about price; show it in captions."))
    assert ok["used_llm"] is True
    bad = rewrite(CARD, api_key="k", post=lambda *a, **k: _Resp("Price questions are 25% of comments."))
    assert bad["used_llm"] is False and "rejected" in bad["reason"]           # invented number refused
    err = rewrite(CARD, api_key="k", post=lambda *a, **k: (_ for _ in ()).throw(ConnectionError()))
    assert err["used_llm"] is False and err["text"].startswith("Put the price")
    assert number_lock_ok("5884 comments", CARD) and not number_lock_ok("6000 comments", CARD)


def test_rewrite_endpoint_disabled_without_key(api_client):
    r = api_client.post("/api/v1/recommendations/REC-X/rewrite")
    assert r.status_code == 501 and "disabled" in r.json()["detail"]
