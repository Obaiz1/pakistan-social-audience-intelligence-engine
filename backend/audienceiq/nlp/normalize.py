"""Privacy-preserving, meaning-preserving normalisation for short multilingual comments.

What it does (and deliberately does not do):
- Unicode NFKC; Arabic-script letter variants folded to Urdu forms (ي/ى→ی, ك→ک, ه→ہ); diacritics removed.
- URLs, @mentions, e-mail addresses and phone numbers are replaced with placeholder tokens (PII never reaches models).
- Emojis become word tokens (emoji_love, emoji_fire, ...) so emoji-only praise can still cluster.
- Latin text is lower-cased; letters repeated 3+ times are squeezed to two ("plzzzz" → "plzz").
- A small, documented Roman Urdu / English spelling-variant map (e.g. "kia"→"kya", "dilivery"→"delivery").
- No stopword removal: short questions like "price?" must keep their meaning.
"""

import re
import unicodedata

_URL = re.compile(r"(https?://\S+|www\.\S+)", re.I)
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_MENTION = re.compile(r"@\w+")
_PHONE = re.compile(r"(?<!\w)(?:\+?92|0)3\d{2}[\s-]?\d{7}(?!\w)")
_DIACRITICS = re.compile(r"[ً-ْٰٕٔ]")
_REPEAT = re.compile(r"([a-z])\1{2,}")
_SPACES = re.compile(r"\s+")
_URDU_CHAR = re.compile(r"[؀-ۿ]")

_ARABIC_TO_URDU = str.maketrans({"ي": "ی", "ى": "ی", "ك": "ک", "ه": "ہ", "ة": "ہ", "ۀ": "ہ", "ؤ": "ؤ"})

EMOJI_GROUPS = {
    "emoji_love": "❤♥💖💗💕💞💓💘💝😍🥰😘💜💙💚🧡🤍🖤🤎",
    "emoji_fire": "🔥✨💯⭐🌟",
    "emoji_like": "👍👌🙌👏",
    "emoji_happy": "😊😀😃😄😁🙂☺😇🤩",
    "emoji_sad": "😢😭😞😔☹🙁💔",
    "emoji_angry": "😡😠🤬😤👎",
    "emoji_pray": "🙏🤲",
    "emoji_think": "🤔🧐",
}
_EMOJI_TO_TOKEN = {ch: tok for tok, chars in EMOJI_GROUPS.items() for ch in chars}
_OTHER_EMOJI = re.compile("[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF]")
_VARIATION = re.compile("[️‍]")

# Spelling variants → canonical form. Only unambiguous variants are listed (e.g. "me" is NOT mapped,
# because it is also English). Written from general knowledge, not tuned on evaluation data.
VARIANTS = {
    "hy": "hai", "hay": "hai", "haii": "hai", "h": "hai",
    "kia": "kya", "kiya": "kya", "kyaa": "kya",
    "kitnay": "kitne", "kitny": "kitne", "kitni": "kitni", "kitna": "kitna",
    "nai": "nahi", "nhi": "nahi", "nahin": "nahi", "ni": "nahi",
    "plz": "please", "pls": "please", "plzz": "please", "plx": "please", "plese": "please", "pleasee": "please",
    "thx": "thanks", "thanku": "thanks", "thankyou": "thanks",
    "dilivery": "delivery", "delivry": "delivery", "dlvry": "delivery", "deliveryy": "delivery", "delievery": "delivery",
    "availble": "available", "avaliable": "available", "avlbl": "available", "avail": "available", "availabe": "available",
    "prise": "price", "prize": "price", "pric": "price",
    "discunt": "discount", "discout": "discount", "dicount": "discount",
    "qeemat": "qeemat", "keemat": "qeemat", "qimat": "qeemat", "kimat": "qeemat",
    "bohot": "bohat", "bahut": "bohat", "buhat": "bohat", "bht": "bohat", "bohut": "bohat",
    "zyada": "zyada", "ziada": "zyada", "zada": "zyada", "ziyada": "zyada",
    "chahye": "chahiye", "chaiye": "chahiye", "chahiay": "chahiye", "chahie": "chahiye",
    "khoobsurat": "khubsurat", "khoobsoorat": "khubsurat", "khubsoorat": "khubsurat",
    "inbx": "inbox", "dm": "dm",
    "msg": "message", "txt": "text",
    "sizee": "size", "sise": "size",
    "kapray": "kapre", "kapry": "kapre",
}
_TOKEN = re.compile(r"emoji_[a-z]+|<[a-z]+>|[a-z0-9]+(?:\.[0-9]+)?|[؀-ۿ]+|[^\sa-z0-9]")


def has_urdu_script(text: str) -> bool:
    return bool(_URDU_CHAR.search(text or ""))


def strip_pii(text: str) -> str:
    """Replace URLs, e-mails, @mentions and Pakistani mobile numbers with placeholder tokens."""
    t = _URL.sub(" <url> ", text or "")
    t = _EMAIL.sub(" <email> ", t)
    t = _PHONE.sub(" <phone> ", t)
    return _MENTION.sub(" <user> ", t)


def emojis_to_tokens(text: str) -> str:
    out = []
    for ch in _VARIATION.sub("", text):
        tok = _EMOJI_TO_TOKEN.get(ch)
        if tok:
            out.append(f" {tok} ")
        elif _OTHER_EMOJI.match(ch):
            out.append(" emoji_other ")
        else:
            out.append(ch)
    return "".join(out)


def normalize_text(text: str | None) -> str:
    """Full normalisation used before language ID, rule labelling and embeddings."""
    if not text:
        return ""
    t = unicodedata.normalize("NFKC", str(text))
    t = strip_pii(t)
    t = emojis_to_tokens(t)
    t = t.translate(_ARABIC_TO_URDU)
    t = _DIACRITICS.sub("", t)
    t = t.lower()
    t = _REPEAT.sub(r"\1\1", t)
    tokens = [VARIANTS.get(tok, tok) for tok in _TOKEN.findall(t)]
    return _SPACES.sub(" ", " ".join(tokens)).strip()


def tokens(text: str) -> list[str]:
    return _TOKEN.findall(text or "")


# Salutations, politeness markers and PII placeholders carry no audience need but dominate short-comment embeddings
# ("AOA sis ... please"). Only these are removed before embedding — never question words, products, sizes or places.
BOILERPLATE = {
    "hi", "hello", "hey", "dear", "aoa", "salam", "assalam", "assalamualaikum", "alaikum", "walaikum", "o", "sis", "appi",
    "baji", "bhai", "team", "please", "kindly", "plz", "pls", "<user>", "<url>", "<email>", "<phone>",
    "السلام", "علیکم", "سلام", "،",
}


def strip_boilerplate(normalized: str) -> str:
    """Remove greeting/politeness/placeholder tokens from already-normalised text; falls back to the input if empty."""
    kept = [t for t in normalized.split() if t not in BOILERPLATE]
    return " ".join(kept) if kept else normalized
