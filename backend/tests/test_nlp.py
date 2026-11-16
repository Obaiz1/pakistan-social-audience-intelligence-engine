import pandas as pd
import pytest

from audienceiq.nlp.intent import label_need, purchase_intent, sentiment
from audienceiq.nlp.langid import detect_language
from audienceiq.nlp.normalize import normalize_text, strip_boilerplate

ASSIGNMENT_EXAMPLES = [  # the eight comments quoted in the assignment brief
    ("Price please?", "price", "english"),
    ("Is this available in Karachi?", "availability", "english"),
    ("Very beautiful dress!", "compliment", "english"),
    ("Price bohat zyada hai.", "price", "roman_urdu"),
    ("Delivery kitne din mein hogi?", "delivery", "roman_urdu"),
    ("Any discount on this suit?", "discount", "english"),
    ("Ordered last week, still waiting.", "order_issue", "english"),
    ("Inbox me details send kar dein.", "purchase_inquiry", "roman_urdu"),
]


@pytest.mark.parametrize("text,need,lang", ASSIGNMENT_EXAMPLES)
def test_assignment_examples(text, need, lang):
    assert label_need(text).topic == need
    assert detect_language(text) == lang


def test_normalize_strips_pii_and_tokenizes_emoji():
    out = normalize_text("Call 0300-1234567 or mail a.b@x.com @sana ❤️😍 https://x.y/z")
    assert "<phone>" in out and "<email>" in out and "<user>" in out and "<url>" in out
    assert "0300" not in out and "x.com" not in out
    assert out.count("emoji_love") == 2


def test_normalize_urdu_letter_forms_and_variants():
    assert normalize_text("كيا") == normalize_text("کیا")        # Arabic kaf/yeh folded to Urdu forms
    assert normalize_text("Price kia hy plzzzz") == "price kya hai please"
    assert normalize_text("") == "" and normalize_text(None) == ""


def test_boilerplate_only_removes_greetings():
    assert strip_boilerplate(normalize_text("AOA sis price kya hai please?")) == "price kya hai ?"
    assert strip_boilerplate("hi") == "hi"                       # never returns empty


def test_language_codes():
    assert detect_language("قیمت کیا ہے؟") == "urdu"
    assert detect_language("❤️❤️❤️") == "other"
    assert detect_language("   ") == "unknown"
    assert detect_language("XL size دستیاب hai?") == "mixed"


def test_unmatched_comment_stays_other_not_forced():
    lab = label_need("Song name?")
    assert lab.topic == "other" and lab.confidence == 0.0


def test_kitne_disambiguation():
    assert label_need("kitne ka hai?").topic == "price"
    assert label_need("kitne din lagenge?").topic == "delivery"
    assert label_need("Discount milega?").topic == "discount"   # weak availability verb defers to the concrete need


def test_purchase_intent_is_not_a_purchase():
    assert purchase_intent("Price please?") == "possible_inquiry"
    assert purchase_intent("Mujhe ye lena hai") == "strong_intent"
    assert purchase_intent("Price bohat zyada hai") == "none"     # complaint, not an inquiry
    assert purchase_intent("") == "unknown"


def test_sentiment_heuristic():
    assert sentiment("Very beautiful dress!") == "positive"
    assert sentiment("Worst service, still waiting") == "negative"
    assert sentiment("Delivery kitne din mein hogi?") == "neutral"


def test_audit_set_langid_and_rule_accuracy():
    from audienceiq.services.datasets import audit_set

    a = audit_set()
    assert len(a) == 100 and set(a["language"]) >= {"english", "roman_urdu", "urdu"}
    lang_acc = (a["text"].map(detect_language) == a["language"]).mean()
    rule_acc = (a["text"].map(lambda t: label_need(t).topic) == a["need"]).mean()
    assert lang_acc >= 0.85, lang_acc
    assert rule_acc >= 0.60, rule_acc
    assert isinstance(a, pd.DataFrame)


def test_gloss_translates_roman_urdu_without_inserting_need_labels():
    from audienceiq.nlp.gloss import embedding_text, gloss

    assert gloss("delivery kitne din mein hogi ?") == "delivery how many days in will be ?"
    assert gloss("order kiya tha abhi tak nahi mila") == "i placed an order still not yet not received"
    # a gloss is a translation: no need label appears unless the source word means it
    for text in ["ye wala bohat pyara hai", "size chart bhej dein", "kab tak aayega"]:
        out = gloss(text)
        for label in ("price", "discount", "delivery", "availability"):
            assert label not in out, (text, out)
    assert embedding_text("price please ?", "english") == "price please ?"          # English untouched
    assert embedding_text("قیمت کیا ہے", "urdu") == "قیمت کیا ہے"                 # Urdu script untouched
