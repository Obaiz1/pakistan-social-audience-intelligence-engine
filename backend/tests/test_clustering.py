from collections import Counter

import numpy as np
import pandas as pd

from audienceiq.clustering.candidates import assign_nearest, fit_hdbscan, fit_kmeans, relabel_by_size
from audienceiq.clustering.evaluate import external_agreement, internal_metrics, stability_ari
from audienceiq.clustering.pipeline import run_clustering
from audienceiq.clustering.profile import ctfidf_terms, name_cluster
from audienceiq.nlp.embeddings import LexicalEmbedder
from audienceiq.nlp.intent import label_need
from audienceiq.nlp.langid import detect_language
from audienceiq.nlp.normalize import normalize_text, strip_boilerplate

# Hand-written multilingual fixture: four needs × English / Roman Urdu / Urdu, several phrasings each.
FIXTURE = {
    "price": ["Price please?", "What is the price?", "price kya hai", "Price kya hai?", "iski price kya hai", "price bata dein",
              "قیمت کیا ہے؟", "قیمت بتا دیں", "price plz", "kindly share the price", "price batao", "what's the price of this"],
    "delivery": ["Delivery to Lahore?", "delivery kitne din mein", "Delivery Karachi mein?", "delivery charges kitne hain",
                 "ڈیلیوری کتنے دن میں ہوگی؟", "ڈیلیوری چارجز؟", "how many days for delivery", "delivery time to multan",
                 "delivery kab tak hogi", "do you deliver to quetta", "delivery islamabad mein hoti hai", "free delivery?"],
    "discount": ["Discount milega?", "any discount?", "koi discount hai", "sale kab lagegi", "ڈسکاؤنٹ ہے؟", "سیل کب لگے گی؟",
                 "discount code please", "is there a sale", "discount kitna hai", "any discount on this", "sale mein aayega",
                 "kya discount hai"],
    "size_fit": ["XL size available hai?", "size chart please", "medium size hai?", "سائز چارٹ بھیج دیں", "XL سائز ہے؟",
                 "do you have XXL", "size guide bhej dein", "large size hai", "small size available?", "size chart bhejo",
                 "kya XL size milega", "what sizes do you have"],
}


def _fixture_frame():
    rows = [{"comment_id": f"c{i}", "comment_text": t, "need": need}
            for i, (need, t) in enumerate((n, t) for n, ts in FIXTURE.items() for t in ts)]
    df = pd.DataFrame(rows)
    df["norm_text"] = df["comment_text"].map(lambda t: strip_boilerplate(normalize_text(t)))
    df["language_type"] = df["comment_text"].map(detect_language)
    df["topic"] = df["comment_text"].map(lambda t: label_need(t).topic)
    df["published_at"] = "2026-01-01T00:00:00Z"
    return df


def test_lexical_clustering_groups_multilingual_needs_nontrivially():
    df = _fixture_frame()
    x = LexicalEmbedder(n_components=20).fit_transform(df["norm_text"].tolist())
    c = fit_kmeans(x, 4, seed=42)
    agreement = external_agreement(c.labels, df["need"].to_numpy())
    # Not hard-coded: the labels come from KMeans on TF-IDF features. Each need should mostly share a cluster.
    assert agreement["purity"] >= 0.6, agreement
    assert c.n_clusters == 4 and len(set(c.labels)) == 4


def test_examples_from_brief_land_with_their_own_need():
    df = _fixture_frame()
    x = LexicalEmbedder(n_components=20).fit_transform(df["norm_text"].tolist())
    c = fit_kmeans(x, 4, seed=42)
    major = {need: Counter(c.labels[df["need"] == need]).most_common(1)[0][0] for need in FIXTURE}
    idx = {t: i for i, t in enumerate(df["comment_text"])}
    hits = sum(c.labels[idx[t]] == major[n] for t, n in [("Price kya hai?", "price"), ("Delivery Karachi mein?", "delivery"),
                                                          ("Discount milega?", "discount"), ("XL size available hai?", "size_fit")])
    assert hits >= 3


def test_relabel_by_size_and_noise_kept():
    labels = relabel_by_size(np.array([5, 5, 5, 2, 2, -1, 9]))
    assert list(labels) == [0, 0, 0, 1, 1, -1, 2]


def test_internal_metrics_and_stability():
    rng = np.random.default_rng(0)
    x = np.vstack([rng.normal(0, 0.05, (40, 5)) + np.eye(5)[i % 3] for i in range(3)])
    x = x / np.linalg.norm(x, axis=1, keepdims=True)
    runs = [fit_kmeans(x, 3, seed=s).labels for s in (1, 2, 3)]
    m = internal_metrics(x, runs[0])
    assert m["n_clusters"] == 3 and m["silhouette_cosine"] > 0.5 and m["noise_rate"] == 0
    assert stability_ari(runs) > 0.95


def test_hdbscan_marks_noise_and_nearest_assignment():
    rng = np.random.default_rng(1)
    x = np.vstack([rng.normal(0, 0.02, (60, 8)) + 1, rng.normal(0, 0.02, (60, 8)) - 1, rng.uniform(-3, 3, (6, 8))])
    c = fit_hdbscan(x, min_cluster_size=20, dims=4)
    assert c.n_clusters >= 2
    cid, dist = assign_nearest(c.centroids[:1], c.centroids)
    assert cid[0] == 0 and dist[0] < 1e-5


def test_naming_reports_mixed_below_threshold():
    assert name_cluster(Counter({"price": 8, "discount": 2}))[1] == "price"
    label, need, agreement = name_cluster(Counter({"price": 4, "discount": 3, "delivery": 3}))
    assert need == "mixed" and label.startswith("Mixed") and agreement == 0.4


def test_ctfidf_terms_are_distinctive():
    terms = ctfidf_terms(["price kya hai", "price please", "delivery kab", "delivery charges"], np.array([0, 0, 1, 1]))
    assert terms[0][0] == "price" and terms[1][0] == "delivery"


def test_pipeline_selection_is_reproducible_and_reports_external_only():
    df = _fixture_frame()
    x = LexicalEmbedder(n_components=20).fit_transform(df["norm_text"].tolist())
    kwargs = dict(embeddings={"lexical": (x, "test")}, k_values=[3, 4, 5], hdbscan_sizes=[], seed=42,
                  truth={"need": df["need"].to_numpy()})
    a = run_clustering(df, "t", **kwargs)
    b = run_clustering(df, "t", **kwargs)
    assert a.selected["run_id"] == b.selected["run_id"]
    assert (a.labels == b.labels).all()
    assert a.runs["selected"].sum() == 1
    cands = a.evaluation["candidates"]
    assert all("need" in c["external"] for c in cands)          # reported...
    assert "external" not in a.evaluation["selection_rule"]["score"]  # ...but not part of the selection score
    assert len(a.assignments) == len(df) and set(a.profile_rows["cluster_id"]) == set(a.labels)
