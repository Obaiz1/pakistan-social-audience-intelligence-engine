"""Roman Urdu → English word/phrase gloss, applied to embedding input only.

Why: multilingual sentence encoders are trained mostly on standard scripts and understand Roman Urdu (Urdu written in
Latin letters) poorly — on the independent audit set, Roman Urdu comments were the worst-recovered language. A gloss
translates the most frequent Roman Urdu function words and everyday commerce phrases into English *translations*
(e.g. "kitne din" → "how many days", "nahi mila" → "not received"), so the encoder sees meaning instead of
unfamiliar tokens. It never inserts need labels ("price", "delivery") that are not a translation of the source words.

Written from general knowledge of Roman Urdu, not tuned on evaluation data. Unknown words are kept unchanged, and the
stored comment text is never modified (only the embedding input).
"""

import re

# Longest phrases first (applied in order).
PHRASES = [
    ("kitne din", "how many days"), ("kitni der", "how long"), ("kab tak", "by when"), ("abhi tak", "still not yet"),
    ("nahi mila", "not received"), ("nahi mili", "not received"), ("nahi aaya", "has not arrived"),
    ("nahi aya", "has not arrived"), ("order kiya tha", "i placed an order"), ("order kiya", "i ordered"),
    ("mil jayega", "will be available"), ("mil jaye", "will be available"), ("mil sakta", "can be available"),
    ("mil skta", "can be available"), ("kitne ka", "how much is"), ("kitne ki", "how much is"), ("kitne ke", "how much are"),
    ("bata dein", "please tell"), ("bata do", "please tell"), ("bhej dein", "please send"), ("bhej do", "please send"),
    ("kar dein", "please do"), ("lena hai", "want to buy"), ("leni hai", "want to buy"), ("karna hai", "want to do"),
    ("sale kab", "when is the sale"), ("kab lagegi", "when will it start"), ("dobara kab", "when again"),
    ("masha allah", "wow"), ("eid se pehle", "before eid"), ("koi jawab nahi", "no reply"), ("reply nahi", "no reply"),
]
WORDS = {
    "hai": "is", "hain": "are", "tha": "was", "thi": "was", "kya": "what", "kia": "what", "nahi": "not", "mein": "in",
    "ka": "of", "ki": "of", "ke": "of", "ko": "to", "se": "from", "ye": "this", "yeh": "this", "is": "this",
    "wala": "one", "wali": "one", "bohat": "very", "zyada": "too much", "mehnga": "expensive", "mehenga": "expensive",
    "sasta": "cheap", "qeemat": "price", "kitna": "how much", "kitne": "how many", "kitni": "how much", "kab": "when",
    "kahan": "where", "kaise": "how", "kaisa": "how", "kaisi": "how", "kapra": "fabric", "kapre": "fabric", "rang": "colour",
    "milega": "will be available", "milegi": "will be available", "milenge": "will be available", "batao": "tell",
    "bataen": "tell", "batayein": "tell", "bhejo": "send", "bhejein": "send", "chahiye": "need", "aayega": "will come",
    "ayega": "will come", "hogi": "will be", "hoga": "will be", "pohanchega": "will arrive", "lagenge": "will take",
    "pyara": "lovely", "pyari": "lovely", "pyare": "lovely", "khubsurat": "beautiful", "zabardast": "excellent",
    "kamal": "amazing", "kamaal": "amazing", "acha": "good", "achi": "good", "kharab": "damaged", "ghalat": "wrong",
    "patla": "thin", "mota": "thick", "lambai": "length", "chota": "small", "bara": "large", "jawab": "reply",
    "dobara": "again", "abhi": "now", "pehle": "before", "baad": "after", "aur": "and", "bhi": "also", "kar": "do",
    "dein": "please", "karein": "do", "mujhe": "i", "mera": "my", "meri": "my", "aap": "you", "koi": "any",
    "lagta": "seems", "silai": "stitching", "dupatta": "scarf", "jora": "suit", "intezar": "waiting", "din": "days",
    "hafte": "weeks", "mulk": "country", "bahar": "abroad", "hota": "is", "jata": "goes",
}
_PHRASE_RX = [(re.compile(rf"(?<![\w]){re.escape(a)}(?![\w])"), b) for a, b in PHRASES]


def gloss(normalized: str) -> str:
    """Translate frequent Roman Urdu words/phrases in already-normalised text; other tokens are kept."""
    t = normalized
    for rx, rep in _PHRASE_RX:
        t = rx.sub(rep, t)
    return " ".join(WORDS.get(tok, tok) for tok in t.split())


GLOSS_LANGUAGES = {"roman_urdu", "mixed"}


def embedding_text(display_text: str, language: str) -> str:
    """Embedding input: boilerplate-stripped normalised text, glossed when the comment is Roman Urdu / mixed."""
    return gloss(display_text) if language in GLOSS_LANGUAGES else display_text
