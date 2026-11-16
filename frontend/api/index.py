"""Vercel Python entrypoint. The backend package and the committed dataset bundles are copied into .backend/ at build
time by scripts/prepare-backend.mjs (pattern reused from Repo B signalspend-ai @9c5f415)."""
import sys
from pathlib import Path

source = Path(__file__).resolve().parents[1] / ".backend"
sys.path.insert(0, str(source))

from audienceiq.api.app import app  # noqa: E402, F401
