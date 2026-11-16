"""Runtime settings read from the environment. Secrets are never logged or returned by the API."""

import os
from dataclasses import dataclass
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent


def _repo_root() -> Path:
    # Local checkout: backend/audienceiq -> repo root. Vercel bundle: .backend/audienceiq -> .backend.
    env = os.environ.get("AUDIENCEIQ_ROOT")
    if env:
        return Path(env)
    return PACKAGE_DIR.parent.parent if (PACKAGE_DIR.parent.parent / "data").exists() else PACKAGE_DIR.parent


ROOT = _repo_root()


def _flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    var_dir: Path
    hosted: bool
    allow_writes: bool
    max_upload_bytes: int
    app_env: str
    llm_enabled: bool

    @property
    def writes_enabled(self) -> bool:
        return (not self.hosted) or self.allow_writes


def get_settings() -> Settings:
    hosted = _flag("AUDIENCEIQ_HOSTED") or os.environ.get("VERCEL") == "1"
    data_dir = Path(os.environ.get("AUDIENCEIQ_DATA_DIR") or (ROOT / "data"))
    var_dir = Path(os.environ.get("AUDIENCEIQ_VAR_DIR") or (Path("/tmp/audienceiq") if hosted else ROOT / "var"))
    try:
        max_upload = int(os.environ.get("AUDIENCEIQ_MAX_UPLOAD_BYTES") or 2 * 1024 * 1024)
    except ValueError:
        max_upload = 2 * 1024 * 1024
    return Settings(
        data_dir=data_dir,
        var_dir=var_dir,
        hosted=hosted,
        allow_writes=_flag("AUDIENCEIQ_ALLOW_WRITES"),
        max_upload_bytes=max(1024, min(max_upload, 4 * 1024 * 1024)),
        app_env=os.environ.get("APP_ENV", "production" if hosted else "local"),
        llm_enabled=_flag("AUDIENCEIQ_ENABLE_LLM") and bool(os.environ.get("NVIDIA_API_KEY")) and not hosted,
    )
