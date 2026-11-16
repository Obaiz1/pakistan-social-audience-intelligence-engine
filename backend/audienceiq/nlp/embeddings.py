"""Comment embedding backends.

- lexical  : TF-IDF over word 1–2-grams + character 2–5-grams (char_wb), reduced with TruncatedSVD and L2-normalised.
             Explainable baseline; handles Roman Urdu spelling variants through shared character n-grams; needs only
             scikit-learn, so it is the representation used for runtime clustering of imported CSVs.
- semantic : sentence-transformers `paraphrase-multilingual-MiniLM-L12-v2` (Apache-2.0, 118M parameters, 384-d,
             trained on 50+ languages incl. Urdu). OFFLINE ONLY (torch); embeddings are cached on disk.
- hybrid   : [w · semantic, (1 − w) · lexical] concatenated and re-normalised, so cross-lingual meaning and
             Roman-Urdu surface forms both count.
"""

import hashlib
from pathlib import Path

import numpy as np
from scipy.sparse import hstack
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

SEMANTIC_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
LEXICAL_NAME = "tfidf-word1-2+char2-5-svd100"
TOKEN_PATTERN = r"(?u)emoji_[a-z]+|<[a-z]+>|[\w؀-ۿ]+|\?"


class LexicalEmbedder:
    name = "lexical"
    model = LEXICAL_NAME

    def __init__(self, n_components: int = 100, seed: int = 42):
        self.n_components = n_components
        self.seed = seed
        self.word = TfidfVectorizer(token_pattern=TOKEN_PATTERN, ngram_range=(1, 2), min_df=2, sublinear_tf=True,
                                    max_features=40_000)
        self.char = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=2, sublinear_tf=True,
                                    max_features=60_000)
        self.svd: TruncatedSVD | None = None

    def fit_transform(self, texts: list[str]) -> np.ndarray:
        texts = [t or "<empty>" for t in texts]
        x = hstack([self.word.fit_transform(texts), self.char.fit_transform(texts)]).tocsr()
        k = max(2, min(self.n_components, x.shape[1] - 1, x.shape[0] - 1))
        self.svd = TruncatedSVD(n_components=k, random_state=self.seed)
        return normalize(self.svd.fit_transform(x)).astype(np.float32)

    def transform(self, texts: list[str]) -> np.ndarray:
        if self.svd is None:
            raise RuntimeError("fit_transform must be called first")
        texts = [t or "<empty>" for t in texts]
        x = hstack([self.word.transform(texts), self.char.transform(texts)]).tocsr()
        return normalize(self.svd.transform(x)).astype(np.float32)


def semantic_available() -> bool:
    try:
        import sentence_transformers  # noqa: F401
        return True
    except Exception:  # pragma: no cover - depends on optional install
        return False


class SemanticEmbedder:
    name = "semantic"
    model = SEMANTIC_MODEL

    def __init__(self, cache_dir: Path | None = None, batch_size: int = 128):
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(SEMANTIC_MODEL, device="cpu")
        self.version = getattr(self._model, "model_card_data", None) and SEMANTIC_MODEL
        self.cache_dir = cache_dir
        self.batch_size = batch_size

    def _cache_path(self, texts: list[str]) -> Path | None:
        if not self.cache_dir:
            return None
        digest = hashlib.sha256(("\n".join(texts) + SEMANTIC_MODEL).encode("utf-8")).hexdigest()[:20]
        return self.cache_dir / f"semantic-{digest}.npy"

    def encode(self, texts: list[str]) -> np.ndarray:
        texts = [t or "<empty>" for t in texts]
        path = self._cache_path(texts)
        if path and path.exists():
            return np.load(path)
        unique = list(dict.fromkeys(texts))
        vecs = self._model.encode(unique, batch_size=self.batch_size, show_progress_bar=False,
                                  normalize_embeddings=True, convert_to_numpy=True).astype(np.float32)
        lookup = {t: i for i, t in enumerate(unique)}
        out = vecs[[lookup[t] for t in texts]]
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)
            np.save(path, out)
        return out

    fit_transform = encode
    transform = encode


def hybrid(semantic: np.ndarray, lexical: np.ndarray, weight: float = 0.6) -> np.ndarray:
    return normalize(np.hstack([semantic * weight, lexical * (1 - weight)])).astype(np.float32)
