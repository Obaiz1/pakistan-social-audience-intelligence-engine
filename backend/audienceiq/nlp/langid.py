"""Language ID for short social comments.

Adapted from Repo A (pakistani-social-media-content-detective, src/nlp/langid.py @957e3b6):
script decides Urdu vs Latin; for Latin text a lexicon of common Roman Urdu words is compared with
English function words. Project 3 changes: output codes follow the assignment (english / roman_urdu /
urdu / mixed / other / unknown), mixed-script comments are recognised, emoji tokens are ignored, and a
short fashion-commerce Roman Urdu list was added (written from general knowledge, NOT tuned on the
evaluation sets; accuracy is measured in docs/CLUSTERING_EVALUATION.md).
"""

import re

from audienceiq.nlp.normalize import normalize_text

_URDU = re.compile(r"[؀-ۿ]")
_LATIN_WORD = re.compile(r"[a-z]+")

ROMAN_URDU = set("""
hai hain hy hn ha he hay ho hoga hogi hogya hua hui huay tha thi thay the nahi nai nhi na mat bhi bi
kya kia kiya kyun kyu kab kb kahan kaha kidhar kaise kese kaisa kesa kitna kitne kitni kon kaun konsa
ka ki ke ko se sy say mein main mai mn par pr pe tak tk aur wala wali walay wale
yeh ye yah woh wo vo isse usse inka unka apka apki apke aap ap tum tu mera meri mere mujhe mujy
hamara hamari humara hum ham koi kuch kch sab sub sirf srf bas bohat bohut bht bahut buhat zyada ziada
acha achha acchi achi achay ache bura buri bure kharab ganda gandi bakwas bekar bekaar zabardast
khubsurat khoobsurat pyara pyari pyaari sundar mehnga mehenga sasta kapra kapre kapray kapry jora
chahiye chahye chaiye chaey karo kren karein kar kr krna karna krty karte kerty dein dain de do
lagta lagti lagra lagri lagriya laga lagi raha rahi rahe rha rhi gya gaya gayi gye mil mila mili
yaar yar bhai bhae appi baji jaan jani shukriya shukria masha mashallah inshallah subhan allah
abhi ab phir fir pehle pehlay baad jab tab agar lekin magar kyunki
milega milegi milenge milay mile bata batao batayein btain bataen bhej bhejo bhejein bhejdo bhijwa
lena leni lene din hafta hafte qeemat keemat qimat rang silai wapas wapis mangwana mangwaya pohanch
pohnch pohanchi pohncha dikhao dekho kab tak hoga kamal kamaal aap ka apna apni wapsi abhi tak
kaisi kaise kesi kitnay kitny hogi hoga dain dein deejiye dijiye krdein kardein
""".split())

ENGLISH = set("""
the a an is are was were be been am i you he she it we they my your his her our their this that these
those what which who whom when where why how and or but if so very too not no yes do does did have has
had will would can could should of in on at to for from with by about as please plz pls thanks thank
love like nice good great best beautiful amazing awesome gorgeous wow price dress collection
""".split())

LANGUAGE_CODES = ("english", "roman_urdu", "urdu", "mixed", "other", "unknown")


def detect_language(text: str | None) -> str:
    raw = text or ""
    if not raw.strip():
        return "unknown"
    norm = normalize_text(raw)
    norm = re.sub(r"emoji_[a-z]+|<[a-z]+>", " ", norm)
    urdu_chars = len(_URDU.findall(norm))
    words = _LATIN_WORD.findall(norm)
    latin_chars = sum(len(w) for w in words)
    if not urdu_chars and not words:
        return "other"                       # emoji-only / punctuation / digits
    if urdu_chars and latin_chars:
        share = urdu_chars / (urdu_chars + latin_chars)
        if 0.2 <= share <= 0.8 and latin_chars >= 3:
            return "mixed"
    if urdu_chars and urdu_chars >= latin_chars:
        return "urdu"
    ru = sum(w in ROMAN_URDU for w in words)
    en = sum(w in ENGLISH for w in words)
    if ru == 0:
        if en == 0 and len(words) == 1 and len(words[0]) <= 2:
            return "other"
        return "english"
    if en >= 2 and ru >= 2 and min(en, ru) / max(en, ru) >= 0.5:
        return "mixed"
    return "roman_urdu" if ru >= en else "english"
