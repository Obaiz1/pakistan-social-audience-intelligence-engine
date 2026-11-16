"""Clustering algorithms compared for comment discovery (unsupervised; no need labels are used to fit).

- KMeans on L2-normalised embeddings (≈ spherical k-means / cosine), k swept over a range; every comment gets a cluster.
- HDBSCAN (scikit-learn implementation) on a PCA-reduced copy of the embeddings; finds a variable number of dense
  groups and marks low-density comments as noise (-1) instead of forcing them into a group.
"""

from dataclasses import dataclass, field

import numpy as np
from sklearn.cluster import HDBSCAN, KMeans
from sklearn.decomposition import PCA


@dataclass
class Candidate:
    algorithm: str
    params: dict
    labels: np.ndarray
    centroids: np.ndarray
    seed: int
    extra: dict = field(default_factory=dict)

    @property
    def n_clusters(self) -> int:
        return int(len(set(self.labels.tolist()) - {-1}))

    @property
    def noise_rate(self) -> float:
        return float((self.labels == -1).mean()) if len(self.labels) else 0.0

    @property
    def key(self) -> str:
        p = ",".join(f"{k}={v}" for k, v in sorted(self.params.items()))
        return f"{self.algorithm}({p})"


def centroids_for(x: np.ndarray, labels: np.ndarray) -> np.ndarray:
    ids = sorted(set(labels.tolist()) - {-1})
    if not ids:
        return np.zeros((0, x.shape[1]), dtype=np.float32)
    cents = np.vstack([x[labels == c].mean(axis=0) for c in ids])
    norms = np.linalg.norm(cents, axis=1, keepdims=True)
    return (cents / np.where(norms == 0, 1, norms)).astype(np.float32)


def relabel_by_size(labels: np.ndarray) -> np.ndarray:
    """Cluster 0 = largest group, 1 = next, ...; noise stays -1. Makes IDs stable and readable."""
    ids = [c for c in set(labels.tolist()) if c != -1]
    order = sorted(ids, key=lambda c: (-(labels == c).sum(), c))
    mapping = {old: new for new, old in enumerate(order)}
    return np.array([mapping.get(int(c), -1) for c in labels], dtype=int)


def fit_kmeans(x: np.ndarray, k: int, seed: int = 42, sample_weight: np.ndarray | None = None) -> Candidate:
    km = KMeans(n_clusters=k, n_init=10, random_state=seed)
    labels = relabel_by_size(km.fit_predict(x, sample_weight=sample_weight))
    return Candidate("kmeans", {"k": k}, labels, centroids_for(x, labels), seed, {"inertia": float(km.inertia_)})


def reduce(x: np.ndarray, method: str = "pca", dims: int = 10, seed: int = 42) -> tuple[np.ndarray, str]:
    """Dimensionality reduction before density clustering. UMAP (offline, optional dependency) or PCA."""
    dims = min(dims, x.shape[1], max(2, x.shape[0] - 2))
    if method == "umap":
        try:
            from umap import UMAP

            red = UMAP(n_components=dims, n_neighbors=15, min_dist=0.0, metric="cosine", random_state=seed)
            return red.fit_transform(x), "umap"
        except ImportError:
            method = "pca"
    return PCA(n_components=dims, random_state=seed).fit_transform(x), "pca"


def fit_hdbscan(x: np.ndarray, min_cluster_size: int, min_samples: int = 10, dims: int = 10, seed: int = 42,
                reducer: str = "pca", reduced: np.ndarray | None = None) -> Candidate:
    used = reducer
    if reduced is None:
        reduced, used = reduce(x, reducer, dims, seed)
    model = HDBSCAN(min_cluster_size=min_cluster_size, min_samples=min_samples, cluster_selection_method="eom",
                    copy=True)
    labels = relabel_by_size(model.fit_predict(reduced))
    return Candidate("hdbscan", {"min_cluster_size": min_cluster_size, "min_samples": min_samples, "reducer": used,
                                 "dims": int(reduced.shape[1])}, labels, centroids_for(x, labels), seed)


def assign_nearest(x: np.ndarray, centroids: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Nearest-centroid (cosine) assignment for new comments; returns (cluster_id, cosine distance)."""
    if len(centroids) == 0:
        return np.full(len(x), -1), np.full(len(x), np.nan)
    sims = x @ centroids.T
    best = sims.argmax(axis=1)
    return best.astype(int), (1 - sims[np.arange(len(x)), best]).astype(np.float32)
