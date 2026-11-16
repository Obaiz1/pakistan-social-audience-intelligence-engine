"""Clustering quality metrics. Internal metrics need no labels; external metrics are reported, never used to select.

All metrics are computed on clustered (non-noise) comments; the noise rate is reported alongside so a model cannot
look good simply by discarding hard comments.
"""

import numpy as np
from sklearn.metrics import (
    adjusted_rand_score,
    calinski_harabasz_score,
    davies_bouldin_score,
    normalized_mutual_info_score,
    silhouette_score,
    v_measure_score,
)

SILHOUETTE_SAMPLE = 5000


def internal_metrics(x: np.ndarray, labels: np.ndarray, seed: int = 42) -> dict:
    mask = labels != -1
    ids, counts = np.unique(labels[mask], return_counts=True)
    out = {"n_clusters": int(len(ids)), "noise_rate": round(float(1 - mask.mean()), 4) if len(labels) else 0.0,
           "silhouette_cosine": None, "davies_bouldin": None, "calinski_harabasz": None,
           "min_cluster_share": None, "max_cluster_share": None, "size_entropy": None}
    if len(ids) < 2 or mask.sum() < 3:
        return out
    xs, ls = x[mask], labels[mask]
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(xs), size=min(SILHOUETTE_SAMPLE, len(xs)), replace=False)
    if len(np.unique(ls[idx])) >= 2:
        out["silhouette_cosine"] = round(float(silhouette_score(xs[idx], ls[idx], metric="cosine")), 4)
    out["davies_bouldin"] = round(float(davies_bouldin_score(xs, ls)), 4)
    out["calinski_harabasz"] = round(float(calinski_harabasz_score(xs, ls)), 1)
    shares = counts / counts.sum()
    out["min_cluster_share"] = round(float(shares.min()), 4)
    out["max_cluster_share"] = round(float(shares.max()), 4)
    out["size_entropy"] = round(float(-(shares * np.log(shares)).sum() / np.log(len(shares))), 4)
    return out


def external_agreement(labels: np.ndarray, reference: np.ndarray, include_noise: bool = False) -> dict:
    """Agreement between discovered clusters and a reference labelling (e.g. synthetic latent need, language)."""
    mask = np.ones(len(labels), bool) if include_noise else labels != -1
    a, b = labels[mask], np.asarray(reference)[mask]
    if len(a) == 0:
        return {"ari": None, "nmi": None, "v_measure": None, "purity": None}
    purity = 0
    for c in np.unique(a):
        _, cnt = np.unique(b[a == c], return_counts=True)
        purity += cnt.max()
    return {"ari": round(float(adjusted_rand_score(b, a)), 4), "nmi": round(float(normalized_mutual_info_score(b, a)), 4),
            "v_measure": round(float(v_measure_score(b, a)), 4), "purity": round(float(purity / len(a)), 4)}


def stability_ari(label_sets: list[np.ndarray]) -> float | None:
    """Mean pairwise ARI between labelings of the same comments (different seeds / bootstrap refits)."""
    if len(label_sets) < 2:
        return None
    scores = [adjusted_rand_score(label_sets[i], label_sets[j])
              for i in range(len(label_sets)) for j in range(i + 1, len(label_sets))]
    return round(float(np.mean(scores)), 4)


def bootstrap_stability(fit_fn, x: np.ndarray, n_rounds: int = 4, frac: float = 0.8, seed: int = 42) -> float | None:
    """Refit on random 80% subsamples; ARI on the comments shared by each pair of subsamples."""
    rng = np.random.default_rng(seed)
    runs = []
    for r in range(n_rounds):
        idx = np.sort(rng.choice(len(x), size=int(len(x) * frac), replace=False))
        runs.append((idx, fit_fn(x[idx], seed + r + 1)))
    scores = []
    for i in range(len(runs)):
        for j in range(i + 1, len(runs)):
            common, ia, ib = np.intersect1d(runs[i][0], runs[j][0], return_indices=True)
            if len(common) > 10:
                scores.append(adjusted_rand_score(runs[i][1][ia], runs[j][1][ib]))
    return round(float(np.mean(scores)), 4) if scores else None
