"""Fit, compare and select comment-clustering candidates; produce run, assignment and profile tables.

Selection rule (ADR-007, fixed before results were inspected and applied mechanically here):
  eligible  = noise_rate <= MAX_NOISE, every cluster >= MIN_CLUSTER_SHARE of clustered comments, 2 <= k <= MAX_K
  stage 1   = rank eligible candidates by cosine silhouette (fixed 5,000-comment sample)
  stage 2   = for the top STABILITY_TOP candidates, stability = mean pairwise ARI across reseeded (KMeans) or
              80%-bootstrap (HDBSCAN) refits
  selected  = argmax(silhouette × stability)
External agreement (synthetic latent need, language, rule labels) is computed for every candidate and REPORTED ONLY.
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime

import numpy as np
import pandas as pd

from audienceiq.clustering.candidates import Candidate, centroids_for, fit_hdbscan, fit_kmeans, reduce
from audienceiq.clustering.evaluate import (
    bootstrap_stability,
    external_agreement,
    internal_metrics,
    stability_ari,
)
from audienceiq.clustering.profile import build_profiles, profiles_to_rows

MODEL_VERSION = "clustering-v1.0"
MAX_NOISE = 0.35
MIN_CLUSTER_SHARE = 0.01
MAX_K = 40
STABILITY_TOP = 4
STABILITY_SEEDS = 3


@dataclass
class ClusteringResult:
    runs: pd.DataFrame
    assignments: pd.DataFrame
    profiles: list[dict]
    profile_rows: pd.DataFrame
    selected: dict
    x: np.ndarray
    labels: np.ndarray
    centroids: np.ndarray
    evaluation: dict = field(default_factory=dict)


def _kmeans_unique(x: np.ndarray, keys: list[str], k: int, seed: int) -> Candidate:
    """KMeans on unique normalised texts weighted by frequency (same objective as on all rows, much faster)."""
    uniq = list(dict.fromkeys(keys))
    pos = {t: i for i, t in enumerate(uniq)}
    first = {}
    for i, t in enumerate(keys):
        first.setdefault(t, i)
    xu = x[[first[t] for t in uniq]]
    weights = np.bincount([pos[t] for t in keys], minlength=len(uniq)).astype(float)
    k = min(k, len(uniq))
    cand = fit_kmeans(xu, k, seed=seed, sample_weight=weights)
    labels = cand.labels[[pos[t] for t in keys]]
    return Candidate("kmeans", {"k": k}, labels, centroids_for(x, labels), seed, cand.extra)


def _run_id(dataset_id: str, embedding: str, cand: Candidate) -> str:
    h = hashlib.sha1(f"{dataset_id}|{embedding}|{cand.key}|{cand.seed}".encode()).hexdigest()[:8]
    return f"clu-{h}"


def run_clustering(comments: pd.DataFrame, dataset_id: str, embeddings: dict[str, tuple[np.ndarray, str]],
                   k_values: list[int], hdbscan_sizes: list[int], seed: int = 42, show_text: bool = True,
                   truth: dict[str, np.ndarray] | None = None, preferred: str | None = None,
                   hdbscan_reducer: str = "pca") -> ClusteringResult:
    """comments: comment_id, comment_text, norm_text, language_type, topic, published_at (row-aligned with embeddings).

    embeddings: name -> (matrix, model description). truth: optional reference labelings for reporting only.
    """
    keys = comments["norm_text"].tolist()
    now = datetime.now(UTC).isoformat(timespec="seconds")
    reference = {"rule_topic": comments["topic"].to_numpy(), "language": comments["language_type"].to_numpy()}
    if truth:
        reference.update(truth)
    cands: list[dict] = []
    for emb_name, (x, model) in embeddings.items():
        for k in k_values:
            if k >= len(set(keys)):
                continue
            c = _kmeans_unique(x, keys, k, seed)
            cands.append({"embedding": emb_name, "model": model, "cand": c, "x": x})
        sizes = [m for m in hdbscan_sizes if len(x) > 3 * m]
        if sizes:
            reduced, used = reduce(x, hdbscan_reducer, 10, seed)
            for mcs in sizes:
                cand = fit_hdbscan(x, mcs, seed=seed, reduced=reduced)
                cand.params["reducer"] = used
                cands.append({"embedding": emb_name, "model": model, "cand": cand, "x": x, "reducer": used})
    if not cands:
        raise ValueError("Not enough distinct comments to cluster.")

    for item in cands:
        c = item["cand"]
        item["metrics"] = internal_metrics(item["x"], c.labels, seed=seed)
        item["external"] = {name: external_agreement(c.labels, ref) for name, ref in reference.items()}
        m = item["metrics"]
        item["eligible"] = bool(m["silhouette_cosine"] is not None and m["noise_rate"] <= MAX_NOISE
                                and (m["min_cluster_share"] or 0) >= MIN_CLUSTER_SHARE and 2 <= c.n_clusters <= MAX_K)
        item["stability"] = None

    pool = [i for i in cands if i["eligible"] and (preferred is None or i["embedding"] == preferred)] or \
           [i for i in cands if i["eligible"]] or cands
    pool.sort(key=lambda i: -(i["metrics"]["silhouette_cosine"] or -1))
    for item in pool[:STABILITY_TOP]:
        c, x = item["cand"], item["x"]
        if c.algorithm == "kmeans":
            runs = [c.labels] + [_kmeans_unique(x, keys, c.params["k"], seed + s + 1).labels for s in range(STABILITY_SEEDS - 1)]
            item["stability"] = stability_ari(runs)
        else:
            mcs, red = c.params["min_cluster_size"], c.params.get("reducer", "pca")
            item["stability"] = bootstrap_stability(
                lambda xs, s, mcs=mcs, red=red: fit_hdbscan(xs, max(5, int(mcs * 0.8)), seed=s, reducer=red).labels,
                x, n_rounds=3, seed=seed)
    scored = [i for i in pool[:STABILITY_TOP] if i["stability"] is not None]
    best = max(scored, key=lambda i: i["metrics"]["silhouette_cosine"] * i["stability"]) if scored else pool[0]

    rows = []
    for item in cands:
        c = item["cand"]
        item["run_id"] = _run_id(dataset_id, item["embedding"], c)
        m = dict(item["metrics"], stability_ari=item["stability"], eligible=item["eligible"],
                 selection_score=(round(item["metrics"]["silhouette_cosine"] * item["stability"], 4)
                                  if item["stability"] is not None and item["metrics"]["silhouette_cosine"] else None),
                 external=item["external"])
        rows.append({"run_id": item["run_id"], "dataset_id": dataset_id, "created_at": now, "embedding": item["embedding"],
                     "embedding_model": item["model"], "algorithm": c.algorithm, "params_json": json.dumps(c.params),
                     "seed": c.seed, "n_comments": int(len(c.labels)), "n_clusters": c.n_clusters,
                     "noise_rate": round(c.noise_rate, 4), "metrics_json": json.dumps(m, default=float),
                     "selected": int(item is best), "model_version": MODEL_VERSION})
    runs = pd.DataFrame(rows)

    c, x = best["cand"], best["x"]
    labels, cents = c.labels, c.centroids
    profiles = build_profiles(comments.reset_index(drop=True), x, labels, cents, show_text=show_text)
    sims = np.array([float(x[i] @ cents[lab]) if lab != -1 else np.nan for i, lab in enumerate(labels)])
    assignments = pd.DataFrame({"run_id": best["run_id"], "dataset_id": dataset_id, "comment_id": comments["comment_id"].values,
                                "cluster_id": labels, "distance": np.round(1 - sims, 4), "is_noise": (labels == -1).astype(int)})
    selected = runs[runs["selected"] == 1].iloc[0].to_dict()
    evaluation = {
        "selection_rule": {"max_noise": MAX_NOISE, "min_cluster_share": MIN_CLUSTER_SHARE, "max_k": MAX_K,
                           "stability_top": STABILITY_TOP, "stability_seeds": STABILITY_SEEDS,
                           "score": "silhouette_cosine × stability_ari", "preferred_embedding": preferred},
        "selected_run_id": best["run_id"], "selected_key": f"{best['embedding']}:{c.key}",
        "candidates": [{"run_id": r["run_id"], "embedding": r["embedding"], "algorithm": r["algorithm"],
                        "params": json.loads(r["params_json"]), "n_clusters": r["n_clusters"], "noise_rate": r["noise_rate"],
                        **{k: v for k, v in json.loads(r["metrics_json"]).items()}} for r in rows],
    }
    return ClusteringResult(runs, assignments, profiles, pd.DataFrame(profiles_to_rows(best["run_id"], profiles)),
                            selected, x, labels, cents, evaluation)
