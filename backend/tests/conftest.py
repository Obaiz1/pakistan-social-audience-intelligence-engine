import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))


@pytest.fixture(scope="session")
def small_bundle(tmp_path_factory):
    """A small synthetic bundle (lexical embeddings, 240 posts) written to a temp data dir."""
    from audienceiq.services.datasets import build_synthetic

    data_dir = tmp_path_factory.mktemp("data")
    result = build_synthetic(n_posts=240, seed=11, embedding="lexical", out_dir=data_dir / "datasets",
                             k_values=[4, 6, 8], hdbscan_sizes=[15])
    return data_dir, result


@pytest.fixture()
def api_client(small_bundle, tmp_path, monkeypatch):
    """TestClient over the small bundle; local (writable) mode with a temp var dir."""
    from fastapi.testclient import TestClient

    from audienceiq.storage import repository

    data_dir, _ = small_bundle
    monkeypatch.setenv("AUDIENCEIQ_DATA_DIR", str(data_dir))
    monkeypatch.setenv("AUDIENCEIQ_VAR_DIR", str(tmp_path / "var"))
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.delenv("AUDIENCEIQ_HOSTED", raising=False)
    repository.get_repository.cache_clear()
    from audienceiq.api.app import app

    with TestClient(app) as client:
        yield client
    repository.get_repository.cache_clear()


@pytest.fixture()
def hosted_client(api_client, monkeypatch):
    monkeypatch.setenv("AUDIENCEIQ_HOSTED", "1")
    yield api_client
    os.environ.pop("AUDIENCEIQ_HOSTED", None)
