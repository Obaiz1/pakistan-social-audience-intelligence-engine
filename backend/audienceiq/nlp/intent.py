"""Multilingual REFERENCE labeller for audience needs, purchase intent and (heuristic) sentiment.

Role in Project 3 (ADR-008): this is an interpretation and audit aid. Cluster membership is produced by
embeddings + unsupervised clustering; these keyword rules are used afterwards to (a) name a discovered
cluster by majority vote, with the agreement share reported, and (b) audit clusters. Comments that match
nothing stay "other" with confidence 0 instead of being forced into a need.

Matcher technique adapted from Repo A (src/processing/features.py build_tag_matchers @957e3b6): Latin
keywords match on word boundaries, Urdu-script keywords match as substrings.
"""

import re
from dataclasses import dataclass

from audienceiq.nlp.normalize import normalize_text

# Order = tie-break priority (more specific / more actionable first).
NEED_PATTERNS: dict[str, list[str]] = {
    "order_issue": [
        "still waiting", "not received", "haven't received", "havent received", "didn't receive", "didnt receive",
        "not delivered", "nahi mila", "nahi mili", "nahi aaya", "nahi aya", "nahi pohanch", "abhi tak", "late delivery",
        "delay", "delayed", "wrong size", "wrong item", "wrong colour", "wrong color", "damaged", "refund", "return",
        "exchange", "complaint", "no response", "no reply", "reply nahi", "cancel my order", "cancelled", "worst service",
        "tracking", "ordered", "order kiya", "order kia", "parcel nahi",
        "آرڈر کیا", "ابھی تک", "نہیں ملا", "نہیں ملی", "واپس", "ریفنڈ", "شکایت",
    ],
    "delivery": [
        "delivery", "deliver", "shipping", "ship", "courier", "parcel", "cod", "cash on delivery", "kitne din",
        "kitni der", "how many days", "how long", "how soon", "dispatch", "tcs", "leopards", "home delivery",
        "delivery charges", "shipping charges", "international", "abroad", "outside pakistan", "eid se pehle",
        "before eid", "pohanch", "ڈیلیوری", "ترسیل", "کتنے دن", "پہنچ", "شپنگ",
    ],
    "availability": [
        "available", "availability", "stock", "in stock", "out of stock", "restock", "re stock", "sold out",
        "outlet", "branch", "store mein", "in store", "online available", "دستیاب", "اسٹاک", "آؤٹ لیٹ",
    ],
    "size_fit": [
        "size", "sizes", "xs", "xl", "xxl", "xxxl", "small size", "medium size", "large size", "fitting", "fit",
        "measurement", "measurements", "size chart", "size guide", "length", "lambai", "chest", "waist", "plus size",
        "tight", "loose", "سائز", "فٹنگ", "ناپ", "لمبائی",
    ],
    "price": [
        "price", "prices", "rate", "rates", "cost", "costs", "how much", "kitne ka", "kitne ki", "kitne ke",
        "kitna hai", "kitne ka hai", "qeemat", "rs", "pkr", "rupees", "rupay", "mehnga", "mehenga", "expensive",
        "costly", "overpriced", "sasta", "cheap", "affordable", "budget",
        "قیمت", "کتنے کا", "کتنے کی", "مہنگا", "مہنگی", "ریٹ", "پرائس", "روپے",
    ],
    "discount": [
        "discount", "discounts", "sale", "off", "promo", "promo code", "code", "voucher", "coupon", "offer", "deal",
        "deals", "11.11", "12.12", "black friday", "flat", "clearance", "riayat",
        "رعایت", "ڈسکاؤنٹ", "سیل", "آفر",
    ],
    "fabric_quality": [
        "fabric", "quality", "material", "kapra", "kapre", "cotton", "chiffon", "silk", "khaddar", "lawn quality",
        "colour fade", "color fade", "rang", "colour", "color", "transparent", "see through", "thin", "thick",
        "embroidery", "kadhai", "print quality", "stitching", "original", "soft", "breathable",
        "کپڑا", "کوالٹی", "رنگ", "کڑھائی", "میٹیریل", "لان",
    ],
    "purchase_inquiry": [
        "inbox", "dm", "check dm", "check inbox", "whatsapp", "details", "detail", "send details", "how to order",
        "want to order", "can i order", "order karna", "order kaise", "order krna", "buy", "purchase", "lena hai",
        "leni hai", "lene hain", "chahiye", "book kar", "link", "website", "contact", "number", "msg", "message",
        "ان باکس", "آرڈر", "خریدنا", "لینا ہے", "چاہیے", "تفصیلات", "رابطہ",
    ],
    "compliment": [
        "beautiful", "gorgeous", "stunning", "lovely", "love", "loved", "pretty", "elegant", "classy", "amazing",
        "awesome", "nice", "cute", "wow", "superb", "zabardast", "khubsurat", "pyara", "pyari", "kamal", "kamaal",
        "masha allah", "mashallah", "best", "perfect", "emoji_love", "emoji_fire", "emoji_like", "emoji_happy",
        "خوبصورت", "زبردست", "پیارا", "پیاری", "کمال", "ماشاءاللہ", "ماشااللہ",
    ],
}
NEED_ORDER = list(NEED_PATTERNS)
# Generic "will I get it" verbs: availability only when no other concrete need is present ("discount milega?").
WEAK_AVAILABILITY = ["milega", "milegi", "milenge", "mil jaye", "mil jayega", "mil sakta", "mil sakti", "mil skta",
                     "ملے گا", "ملے گی"]
REQUEST_CUES = ["please", "bhej", "bhejo", "bhejein", "bhej dein", "send", "share", "batao", "bata", "bataen",
                "batayein", "tell", "kindly", "guide", "بتائیں", "بھیج"]

STRONG_INTENT = [
    "want to order", "want to buy", "i will buy", "order karna hai", "order krna hai", "lena hai", "leni hai",
    "lene hain", "book kar do", "book kr do", "confirm my order", "how to order", "order kaise", "add to cart",
    "خریدنا ہے", "لینا ہے", "آرڈر کرنا ہے",
]
INQUIRY_NEEDS = {"price", "availability", "size_fit", "delivery", "discount", "purchase_inquiry", "fabric_quality"}

POSITIVE = ["beautiful", "gorgeous", "stunning", "lovely", "love", "pretty", "elegant", "amazing", "awesome", "nice",
            "cute", "wow", "superb", "zabardast", "khubsurat", "pyara", "pyari", "kamal", "kamaal", "best", "perfect",
            "mashallah", "masha allah", "emoji_love", "emoji_fire", "emoji_like", "emoji_happy", "thanks", "shukriya",
            "خوبصورت", "زبردست", "پیارا", "کمال", "شکریہ"]
NEGATIVE = ["worst", "bad", "kharab", "bakwas", "bekar", "disappointed", "disappointing", "still waiting", "not received",
            "late", "delay", "delayed", "wrong", "damaged", "refund", "fraud", "poor", "pathetic", "overpriced",
            "expensive", "mehnga", "zyada", "nahi mila", "emoji_angry", "emoji_sad", "no response", "complaint",
            "خراب", "بکواس", "مہنگا", "نہیں ملا", "شکایت"]

_URDU = re.compile(r"[؀-ۿ]")


def _compile(words: list[str]) -> re.Pattern:
    parts = []
    for w in words:
        escaped = re.escape(w.lower())
        if _URDU.search(w):
            parts.append(escaped)
            continue
        before = r"(?<![\w.])" if w[0].isalnum() else ""
        after = r"(?![\w])" if w[-1].isalnum() else ""
        parts.append(f"{before}{escaped}{after}")
    return re.compile("|".join(parts))


_NEED_RX = {need: _compile(words) for need, words in NEED_PATTERNS.items()}
_WEAK_AVAIL_RX = _compile(WEAK_AVAILABILITY)
_REQUEST_RX = _compile(REQUEST_CUES)
_STRONG_RX = _compile(STRONG_INTENT)
_POS_RX = _compile(POSITIVE)
_NEG_RX = _compile(NEGATIVE)
# "kitne din" is delivery, "kitne ka" is price: remove the ambiguous bare "kitne" handling entirely.
_PCT_OFF = re.compile(r"\d+\s*%\s*off|\d+\s*%")


@dataclass(frozen=True)
class NeedLabel:
    topic: str            # one of constants.NEEDS
    confidence: float     # share of matched-keyword weight held by the winning need (0 when nothing matched)
    matched: tuple[str, ...]


def label_need(text: str | None, normalized: str | None = None) -> NeedLabel:
    t = normalized if normalized is not None else normalize_text(text)
    scores: dict[str, int] = {}
    for need in NEED_ORDER:
        hits = len(_NEED_RX[need].findall(t))
        if need == "discount":
            hits += len(_PCT_OFF.findall(t))
        if hits:
            scores[need] = hits
    weak = len(_WEAK_AVAIL_RX.findall(t))
    if weak and not scores:
        scores["availability"] = weak
    if not scores:
        return NeedLabel("other", 0.0, ())
    # Complaints about an existing order dominate generic delivery words ("ordered last week, still waiting").
    if "order_issue" in scores and "delivery" in scores:
        scores["order_issue"] += scores.pop("delivery")
    # Praise + a concrete question: the question is the actionable need.
    if "compliment" in scores and len(scores) > 1:
        scores["compliment"] -= 1
        if scores["compliment"] <= 0:
            del scores["compliment"]
    # "inbox / details" next to a concrete need: keep the concrete need.
    if "purchase_inquiry" in scores and len(scores) > 1 and scores["purchase_inquiry"] <= max(
            v for k, v in scores.items() if k != "purchase_inquiry"):
        scores["purchase_inquiry"] = scores["purchase_inquiry"] * 0.5
    total = sum(scores.values())
    best = max(NEED_ORDER, key=lambda n: (scores.get(n, 0), -NEED_ORDER.index(n)))
    return NeedLabel(best, round(scores[best] / total, 3), tuple(sorted(scores)))


def purchase_intent(text: str | None, normalized: str | None = None, need: NeedLabel | None = None) -> str:
    t = normalized if normalized is not None else normalize_text(text)
    if not t:
        return "unknown"
    if _STRONG_RX.search(t):
        return "strong_intent"
    need = need or label_need(text, t)
    asks = "?" in t or "؟" in t or bool(_REQUEST_RX.search(t))
    if need.topic in INQUIRY_NEEDS:
        if not asks and sentiment(text, t) == "negative":
            return "none"                    # a complaint such as "price bohat zyada hai" is not an inquiry
        if asks or need.topic in {"purchase_inquiry", "price", "availability"}:
            return "possible_inquiry"
    if need.topic in {"compliment", "order_issue"}:
        return "none"
    return "unknown"


def sentiment(text: str | None, normalized: str | None = None) -> str:
    """Lexicon heuristic, used only as a supporting signal; questions without polarity words are neutral."""
    t = normalized if normalized is not None else normalize_text(text)
    if not t:
        return "unknown"
    pos, neg = len(_POS_RX.findall(t)), len(_NEG_RX.findall(t))
    if pos > neg:
        return "positive"
    if neg > pos:
        return "negative"
    return "neutral"
