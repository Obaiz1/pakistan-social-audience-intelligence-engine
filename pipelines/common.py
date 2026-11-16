"""Shared helpers for offline pipelines (never imported by the web app)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

CACHE = ROOT / "data" / "cache" / "embeddings"
SEMANTIC_MODELS = {
    # name: (Hugging Face id, query prefix, licence)
    "minilm": ("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", "", "Apache-2.0"),
    "e5-small": ("intfloat/multilingual-e5-small", "query: ", "MIT"),
    "mpnet": ("sentence-transformers/paraphrase-multilingual-mpnet-base-v2", "", "Apache-2.0"),
}


def semantic_encoder(name: str):
    """Return (encode(list[str]) -> np.ndarray, model description). Embeddings are cached per unique text set."""
    import hashlib

    import numpy as np
    from sentence_transformers import SentenceTransformer

    model_id, prefix, licence = SEMANTIC_MODELS[name]
    model = SentenceTransformer(model_id, device="cpu")

    def encode(texts: list[str]):
        texts = [t or "<empty>" for t in texts]
        uniq = list(dict.fromkeys(texts))
        digest = hashlib.sha256(("\n".join(uniq) + model_id).encode("utf-8")).hexdigest()[:20]
        path = CACHE / f"{name}-{digest}.npy"
        if path.exists():
            vecs = np.load(path)
        else:
            vecs = model.encode([prefix + u for u in uniq], batch_size=128, normalize_embeddings=True,
                                show_progress_bar=False, convert_to_numpy=True).astype(np.float32)
            path.parent.mkdir(parents=True, exist_ok=True)
            np.save(path, vecs)
        pos = {u: i for i, u in enumerate(uniq)}
        return vecs[[pos[t] for t in texts]]

    return encode, f"{model_id} ({licence}, sentence-transformers {__import__('sentence_transformers').__version__})"
