"""SQLite canonical store. Dataset bundles (CSV tables + dataset.json) are loaded through schema.sql constraints.

A bundle directory contains one CSV per canonical table plus dataset.json (datasets row, sources, evaluation summary,
file manifest with SHA-256). Loading with PRAGMA foreign_keys = ON re-verifies keys, uniqueness and CHECKs every time.
"""

import csv
import hashlib
import io
import json
import math
import sqlite3
from pathlib import Path

import pandas as pd

SCHEMA = Path(__file__).with_name("schema.sql")
# FK-safe load order (parents first).
TABLE_ORDER = ["campaigns", "posts", "comments", "cluster_runs", "cluster_assignments", "cluster_profiles",
               "anomaly_runs", "anomaly_flags", "anomaly_scores", "recommendations", "pipeline_runs"]
DATASET_COLUMNS = ["dataset_id", "name", "mode", "description", "product_category", "created_at", "snapshot_at",
                   "expires_at", "seed", "generator_version", "text_permission", "disclaimer", "post_count",
                   "comment_count", "manifest_json"]


def connect(path: str | Path = ":memory:", read_only: bool = False) -> sqlite3.Connection:
    if read_only and str(path) != ":memory:":
        conn = sqlite3.connect(f"file:{Path(path).as_posix()}?mode=ro", uri=True, check_same_thread=False)
    else:
        conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    if not read_only:
        conn.executescript(SCHEMA.read_text(encoding="utf-8"))
    return conn


def _columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]


def _value(v):
    if v is None:
        return None
    if isinstance(v, float) and math.isnan(v):
        return None
    if hasattr(v, "item"):
        v = v.item()
    if isinstance(v, float) and math.isnan(v):
        return None
    return v


def insert_frame(conn: sqlite3.Connection, table: str, df: pd.DataFrame) -> int:
    cols = [c for c in _columns(conn, table) if c in df.columns]
    if df.empty:
        return 0
    data = df[cols].astype(object).where(pd.notna(df[cols]), None)
    rows = [tuple(_value(v) for v in row) for row in data.itertuples(index=False, name=None)]
    conn.executemany(f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})", rows)
    return len(rows)


def load_bundle(conn: sqlite3.Connection, dataset: dict, tables: dict[str, pd.DataFrame]) -> None:
    """Insert one dataset atomically; raises sqlite3.IntegrityError on any constraint violation."""
    with conn:
        row = {k: dataset.get(k) for k in DATASET_COLUMNS}
        conn.execute(f"INSERT INTO datasets ({', '.join(DATASET_COLUMNS)}) VALUES ({', '.join('?' * len(DATASET_COLUMNS))})",
                     [row[k] for k in DATASET_COLUMNS])
        src = pd.DataFrame(dataset.get("sources", []))
        if not src.empty:
            insert_frame(conn, "sources", src.assign(dataset_id=dataset["dataset_id"]))
        for t in TABLE_ORDER:
            df = tables.get(t)
            if df is not None and not df.empty:
                if "dataset_id" in _columns(conn, t) and "dataset_id" not in df.columns:
                    df = df.assign(dataset_id=dataset["dataset_id"])
                insert_frame(conn, t, df)


def delete_dataset(conn: sqlite3.Connection, dataset_id: str) -> None:
    with conn:
        for t in reversed(TABLE_ORDER):
            if "dataset_id" in _columns(conn, t):
                conn.execute(f"DELETE FROM {t} WHERE dataset_id = ?", [dataset_id])
        conn.execute("DELETE FROM sources WHERE dataset_id = ?", [dataset_id])
        conn.execute("DELETE FROM datasets WHERE dataset_id = ?", [dataset_id])


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_bundle_dir(directory: Path, dataset: dict, tables: dict[str, pd.DataFrame],
                     extra_files: dict[str, object] | None = None) -> dict:
    """Write CSV tables + dataset.json (with a SHA-256 manifest) deterministically."""
    directory.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for name, df in {**tables, **{k: v for k, v in (extra_files or {}).items() if isinstance(v, pd.DataFrame)}}.items():
        path = directory / f"{name}.csv"
        buf = io.StringIO()
        df.to_csv(buf, index=False, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
        path.write_text(buf.getvalue(), encoding="utf-8", newline="")
        manifest[path.name] = {"sha256": _sha(path), "rows": int(len(df))}
    for name, obj in (extra_files or {}).items():
        if not isinstance(obj, pd.DataFrame):
            path = directory / name
            path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=str), encoding="utf-8", newline="")
            manifest[path.name] = {"sha256": _sha(path)}
    meta = dict(dataset)
    meta["manifest"] = manifest
    meta["manifest_json"] = json.dumps({"files": manifest})
    (directory / "dataset.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False, default=str), encoding="utf-8",
                                            newline="")
    return manifest


def read_bundle_dir(directory: Path) -> tuple[dict, dict[str, pd.DataFrame]]:
    meta = json.loads((directory / "dataset.json").read_text(encoding="utf-8"))
    tables = {}
    for t in TABLE_ORDER:
        path = directory / f"{t}.csv"
        if path.exists():
            tables[t] = pd.read_csv(path, dtype=_DTYPES.get(t), keep_default_na=True, na_values=[""])
    return meta, tables


_DTYPES = {
    "posts": {"likes": "Int64", "comments_count": "Int64", "shares": "Int64", "views": "Int64", "post_id": str,
              "source_post_id": str, "campaign_id": str, "source_url": str, "post_text": str},
    "comments": {"comment_id": str, "post_id": str, "comment_text": str, "like_count": "Int64"},
    "cluster_assignments": {"comment_id": str},
    "anomaly_flags": {"post_id": str},
    "anomaly_scores": {"post_id": str},
}


def verify_manifest(directory: Path) -> list[str]:
    """Return a list of files whose SHA-256 differs from dataset.json (empty = intact)."""
    meta = json.loads((directory / "dataset.json").read_text(encoding="utf-8"))
    bad = []
    for name, info in meta.get("manifest", {}).items():
        path = directory / name
        if not path.exists() or _sha(path) != info["sha256"]:
            bad.append(name)
    return bad
