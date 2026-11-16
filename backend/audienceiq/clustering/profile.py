"""Turn discovered clusters into inspectable audience-need profiles.

Naming is a separate, post-hoc step (ADR-008): a cluster is named after the reference need that most of its members
carry, and the agreement share is always reported. Below MIN_AGREEMENT the cluster is called "Mixed: A / B".
Top terms use class-based TF-IDF (c-TF-IDF, as popularised by BERTopic) over member comments.
"""

import json
from collections import Counter

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer

from audienceiq.constants import LANGUAGE_LABELS, NEED_LABELS

MIN_AGREEMENT = 0.45
TERM_PATTERN = r"(?u)emoji_[a-z]+|[^\W\d_]{2,}|[؀-ۿ]{2,}|\d+\.\d+"
DISPLAY_STOPWORDS = set("""
a an the is are was be to of in on for and or it this that these i you we my me your our u do does can will
any what how when where which who hai hain ho ka ki ke ko se mein me main mai ye yeh wo woh kya ya bhi to
kar kr de do dein ne hi ap aap please plz sis appi bhai hello hi hey dear salam aoa assalam alaikum team
ہے ہیں کا کی کے کو سے میں یہ وہ کیا بھی تو کر دیں نے سلام السلام علیکم
""".split())


def ctfidf_terms(texts: list[str], labels: np.ndarray, top_n: int = 8) -> dict[int, list[str]]:
    ids = sorted(set(labels.tolist()) - {-1})
    if not ids:
        return {}
    docs = [" ".join(t for t, lab in zip(texts, labels, strict=True) if lab == c) for c in ids]
    vec = CountVectorizer(token_pattern=TERM_PATTERN, stop_words=list(DISPLAY_STOPWORDS), min_df=1)
    try:
        counts = vec.fit_transform(docs).toarray().astype(float)
    except ValueError:  # empty vocabulary
        return {c: [] for c in ids}
    vocab = np.array(vec.get_feature_names_out())
    tf = counts / np.maximum(counts.sum(axis=1, keepdims=True), 1)
    avg_words = counts.sum() / len(ids)
    idf = np.log(1 + avg_words / np.maximum(counts.sum(axis=0), 1))
    scores = tf * idf
    return {c: [str(vocab[j]) for j in np.argsort(-scores[i])[:top_n] if scores[i, j] > 0] for i, c in enumerate(ids)}


def name_cluster(need_counts: Counter) -> tuple[str, str, float]:
    total = sum(need_counts.values())
    if not total:
        return "Unlabelled", "other", 0.0
    (top, n1), *rest = need_counts.most_common(2) + [("other", 0)]
    agreement = n1 / total
    if agreement >= MIN_AGREEMENT:
        return NEED_LABELS.get(top, top), top, round(agreement, 4)
    second = rest[0][0]
    return f"Mixed: {NEED_LABELS.get(top, top)} / {NEED_LABELS.get(second, second)}", "mixed", round(agreement, 4)


def build_profiles(comments: pd.DataFrame, x: np.ndarray, labels: np.ndarray, centroids: np.ndarray,
                   show_text: bool) -> list[dict]:
    """comments must have: comment_id, norm_text, comment_text, language_type, topic, published_at (aligned with x)."""
    n_clustered = int((labels != -1).sum())
    terms = ctfidf_terms(comments["norm_text"].tolist(), labels)
    profiles = []
    ids = sorted(set(labels.tolist()))
    for c in ids:
        mask = labels == c
        members = comments[mask]
        need_counts = Counter(members["topic"].tolist())
        lang_counts = Counter(members["language_type"].tolist())
        if c == -1:
            label, need, agreement = "Unclustered (noise)", "noise", 0.0
            cohesion = None
        else:
            label, need, agreement = name_cluster(need_counts)
            cent = centroids[c]
            cohesion = round(float((x[mask] @ cent).mean()), 4)
        size = int(mask.sum())
        exemplars = _exemplars(members, x[mask], centroids[c] if c != -1 else None, show_text)
        dates = members["published_at"].dropna().astype(str)
        share = size / n_clustered if (c != -1 and n_clustered) else size / max(len(labels), 1)
        top_lang = lang_counts.most_common(1)[0] if lang_counts else ("unknown", 0)
        profile = {
            "cluster_id": int(c), "label": label, "need_category": need, "label_source": "reference_rule_majority",
            "label_agreement": agreement, "size": size, "share": round(float(share), 4), "cohesion": cohesion,
            "top_terms": terms.get(c, []),
            "language_mix": {k: v for k, v in lang_counts.most_common()},
            "need_mix": {k: v for k, v in need_counts.most_common()},
            "exemplars": exemplars,
            "date_min": dates.min()[:10] if len(dates) else None, "date_max": dates.max()[:10] if len(dates) else None,
        }
        profile["explanation"] = explain(profile, top_lang)
        profiles.append(profile)
    return profiles


def _exemplars(members: pd.DataFrame, xm: np.ndarray, centroid: np.ndarray | None, show_text: bool,
               per_language: int = 2, total: int = 6) -> list[dict]:
    if not len(members):
        return []
    order = np.argsort(-(xm @ centroid)) if centroid is not None else np.arange(len(members))
    picked, seen, per_lang = [], set(), Counter()
    for i in order:
        row = members.iloc[int(i)]
        key = row["norm_text"]
        if key in seen or per_lang[row["language_type"]] >= per_language:
            continue
        seen.add(key)
        per_lang[row["language_type"]] += 1
        picked.append({"comment_id": row["comment_id"], "language_type": row["language_type"],
                       "text": row["comment_text"] if show_text else None,
                       "similarity": round(float(xm[int(i)] @ centroid), 3) if centroid is not None else None})
        if len(picked) >= total:
            break
    return picked


def explain(p: dict, top_lang: tuple[str, int]) -> str:
    if p["cluster_id"] == -1:
        return (f"{p['size']:,} comments were not dense enough to join any group (HDBSCAN noise). They are kept and "
                "shown separately instead of being forced into a need.")
    terms = ", ".join(p["top_terms"][:5]) or "no distinctive terms"
    lang_share = top_lang[1] / p["size"] if p["size"] else 0
    lang_note = (f" It is dominated by {LANGUAGE_LABELS.get(top_lang[0], top_lang[0])} comments ({lang_share:.0%}), so part of "
                 "what holds it together may be language rather than need." if lang_share >= 0.8 else
                 f" It mixes languages (largest: {LANGUAGE_LABELS.get(top_lang[0], top_lang[0])}, {lang_share:.0%}).")
    if p["need_category"] == "mixed":
        naming = (f"No single reference need covers ≥{MIN_AGREEMENT:.0%} of members (top need {p['label_agreement']:.0%}), "
                  "so it is reported as mixed.")
    else:
        naming = (f"{p['label_agreement']:.0%} of its members carry the reference label '{p['label']}', "
                  "which is how it was named after discovery.")
    return (f"{p['size']:,} comments ({p['share']:.1%} of clustered comments) sit close together in embedding space "
            f"(mean cosine similarity to the centre {p['cohesion']}). Distinctive terms: {terms}. {naming}{lang_note}")


def profiles_to_rows(run_id: str, profiles: list[dict]) -> list[dict]:
    rows = []
    for p in profiles:
        rows.append({
            "run_id": run_id, "cluster_id": p["cluster_id"], "label": p["label"], "need_category": p["need_category"],
            "label_source": p["label_source"], "label_agreement": p["label_agreement"], "size": p["size"],
            "share": p["share"], "cohesion": p["cohesion"],
            "top_terms_json": json.dumps(p["top_terms"], ensure_ascii=False),
            "language_mix_json": json.dumps(p["language_mix"], ensure_ascii=False),
            "need_mix_json": json.dumps(p["need_mix"], ensure_ascii=False),
            "exemplars_json": json.dumps(p["exemplars"], ensure_ascii=False),
            "date_min": p["date_min"], "date_max": p["date_max"], "explanation": p["explanation"],
        })
    return rows
