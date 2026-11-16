"""Dataset repository: built-in bundles (read-only, shipped in data/datasets/) + local user imports (SQLite file).

Built-in bundles are loaded into one in-memory SQLite database at first use (constraints re-checked), then exposed as
pandas frames, cached per dataset. Observed datasets past `expires_at` are listed but their data is not served
(YouTube API policy: refresh or delete within 30 days).
"""

import json
import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path

import pandas as pd

from audienceiq.analytics.engagement import add_engagement
from audienceiq.config import get_settings
from audienceiq.storage import db


class DatasetNotFound(KeyError):
    pass


class DatasetExpired(RuntimeError):
    pass


@dataclass
class DatasetFrames:
    meta: dict
    posts: pd.DataFrame
    comments: pd.DataFrame
    campaigns: pd.DataFrame
    cluster_runs: pd.DataFrame
    assignments: pd.DataFrame
    profiles: pd.DataFrame
    anomaly_run: dict | None
    flags: pd.DataFrame
    scores: pd.DataFrame
    recommendations: pd.DataFrame
    pipeline_runs: pd.DataFrame
    evaluation: dict = field(default_factory=dict)

    @property
    def selected_run(self) -> dict | None:
        sel = self.cluster_runs[self.cluster_runs["selected"] == 1]
        return sel.iloc[0].to_dict() if len(sel) else None

    @property
    def comments_clustered(self) -> pd.DataFrame:
        """Comments joined with their selected-run cluster, the cluster's need, and post dimensions (cached)."""
        cached = self.__dict__.get("_cc")
        if cached is None:
            cached = _clustered(self)
            self.__dict__["_cc"] = cached
        return cached


def _clustered(f: DatasetFrames) -> pd.DataFrame:
    if f.assignments.empty:
        return pd.DataFrame(columns=["comment_id", "cluster_id", "need", "cluster_label"])
    prof = f.profiles[["cluster_id", "need_category", "label"]].rename(
        columns={"need_category": "need", "label": "cluster_label"})
    out = f.comments.merge(f.assignments[["comment_id", "cluster_id", "distance", "is_noise"]], on="comment_id", how="left")
    out = out.merge(prof, on="cluster_id", how="left")
    cols = ["post_id", "brand", "platform", "campaign", "content_type", "published_at"]
    return out.merge(f.posts[cols].rename(columns={"published_at": "post_published_at"}), on="post_id", how="left")


class Repository:
    def __init__(self, data_dir: Path | None = None, var_dir: Path | None = None):
        s = get_settings()
        self.data_dir = data_dir or s.data_dir
        self.var_dir = var_dir or s.var_dir
        self._lock = threading.RLock()
        self._builtin: sqlite3.Connection | None = None
        self._builtin_ids: set[str] = set()
        self._bundle_extras: dict[str, dict] = {}
        self._cache: dict[str, DatasetFrames] = {}

    # ---------- connections ----------
    def builtin(self) -> sqlite3.Connection:
        with self._lock:
            if self._builtin is None:
                conn = db.connect(":memory:")
                root = self.data_dir / "datasets"
                for d in sorted(p for p in root.glob("*") if (p / "dataset.json").exists()) if root.exists() else []:
                    meta, tables = db.read_bundle_dir(d)
                    db.load_bundle(conn, meta, tables)
                    self._builtin_ids.add(meta["dataset_id"])
                    evaluation = d / "evaluation.json"
                    self._bundle_extras[meta["dataset_id"]] = {
                        "evaluation": json.loads(evaluation.read_text(encoding="utf-8")) if evaluation.exists() else {},
                        "sources": meta.get("sources", []), "dir": d}
                self._builtin = conn
            return self._builtin

    def user_db_path(self) -> Path:
        return self.var_dir / "audienceiq_user.sqlite"

    def user(self, create: bool = False) -> sqlite3.Connection | None:
        path = self.user_db_path()
        if not path.exists() and not create:
            return None
        path.parent.mkdir(parents=True, exist_ok=True)
        return db.connect(path)

    # ---------- catalogue ----------
    def list_datasets(self) -> list[dict]:
        out = []
        for conn, builtin in ((self.builtin(), True), (self.user(), False)):
            if conn is None:
                continue
            conn.row_factory = sqlite3.Row
            for r in conn.execute("SELECT * FROM datasets ORDER BY mode DESC, created_at"):
                d = dict(r)
                d["builtin"] = builtin
                d["expired"] = _expired(d)
                d["sources"] = self._sources(conn, d["dataset_id"])
                d.pop("manifest_json", None)
                out.append(d)
            conn.row_factory = None
        order = {"synthetic": 0, "observed": 1, "imported": 2}
        return sorted(out, key=lambda d: (order.get(d["mode"], 3), d["created_at"]))

    def _sources(self, conn, dataset_id: str) -> list[dict]:
        cur = conn.execute("SELECT * FROM sources WHERE dataset_id = ?", [dataset_id])
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row, strict=True)) for row in cur.fetchall()]

    def default_dataset_id(self) -> str | None:
        ds = [d for d in self.list_datasets() if not d["expired"]]
        return ds[0]["dataset_id"] if ds else None

    def _conn_for(self, dataset_id: str) -> tuple[sqlite3.Connection, bool]:
        b = self.builtin()
        if dataset_id in self._builtin_ids:
            return b, True
        u = self.user()
        if u is not None and u.execute("SELECT 1 FROM datasets WHERE dataset_id = ?", [dataset_id]).fetchone():
            return u, False
        raise DatasetNotFound(dataset_id)

    # ---------- frames ----------
    def frames(self, dataset_id: str) -> DatasetFrames:
        with self._lock:
            if dataset_id in self._cache:
                return self._cache[dataset_id]
            conn, builtin = self._conn_for(dataset_id)
            meta = dict(zip([c[0] for c in conn.execute("SELECT * FROM datasets LIMIT 0").description],
                            conn.execute("SELECT * FROM datasets WHERE dataset_id = ?", [dataset_id]).fetchone(),
                            strict=True))
            if _expired(meta):
                raise DatasetExpired(dataset_id)
            meta["sources"] = self._sources(conn, dataset_id)
            meta["builtin"] = builtin

            def q(sql: str) -> pd.DataFrame:
                return pd.read_sql_query(sql, conn, params=[dataset_id])

            runs = q("SELECT * FROM cluster_runs WHERE dataset_id = ? ORDER BY selected DESC, run_id")
            sel = runs[runs["selected"] == 1]["run_id"].tolist()
            sel_id = sel[0] if sel else ""
            assignments = pd.read_sql_query("SELECT * FROM cluster_assignments WHERE run_id = ?", conn, params=[sel_id])
            profiles = pd.read_sql_query("SELECT * FROM cluster_profiles WHERE run_id = ? ORDER BY cluster_id", conn,
                                         params=[sel_id])
            arun = q("SELECT * FROM anomaly_runs WHERE dataset_id = ?")
            posts = q("SELECT * FROM posts WHERE dataset_id = ?")
            for col in ("likes", "comments_count", "shares", "views"):
                posts[col] = pd.to_numeric(posts[col], errors="coerce").astype("Int64")
            extras = self._bundle_extras.get(dataset_id, {})
            evaluation = extras.get("evaluation") or {}
            if not evaluation and not builtin:
                row = conn.execute("SELECT manifest_json FROM datasets WHERE dataset_id = ?", [dataset_id]).fetchone()
                evaluation = (json.loads(row[0]) if row and row[0] else {}).get("evaluation", {})
            frames = DatasetFrames(
                meta=meta, posts=add_engagement(posts) if len(posts) else posts,
                comments=q("SELECT * FROM comments WHERE dataset_id = ?"),
                campaigns=q("SELECT * FROM campaigns WHERE dataset_id = ?"), cluster_runs=runs,
                assignments=assignments, profiles=profiles,
                anomaly_run=arun.iloc[0].to_dict() if len(arun) else None,
                flags=q("SELECT * FROM anomaly_flags WHERE dataset_id = ?"),
                scores=q("SELECT * FROM anomaly_scores WHERE dataset_id = ?"),
                recommendations=q("SELECT * FROM recommendations WHERE dataset_id = ? ORDER BY priority, recommendation_id"),
                pipeline_runs=q("SELECT * FROM pipeline_runs WHERE dataset_id = ?"),
                evaluation=evaluation)
            self._cache[dataset_id] = frames
            return frames

    # ---------- writes (local user store only) ----------
    def save_user_bundle(self, dataset: dict, tables: dict[str, pd.DataFrame]) -> None:
        conn = self.user(create=True)
        with self._lock:
            if conn.execute("SELECT 1 FROM datasets WHERE dataset_id = ?", [dataset["dataset_id"]]).fetchone():
                db.delete_dataset(conn, dataset["dataset_id"])
            db.load_bundle(conn, dataset, tables)
            self._cache.pop(dataset["dataset_id"], None)

    def delete_user_dataset(self, dataset_id: str) -> None:
        if dataset_id in self._builtin_ids:
            raise PermissionError("Built-in datasets cannot be deleted.")
        conn = self.user()
        if conn is None:
            raise DatasetNotFound(dataset_id)
        with self._lock:
            db.delete_dataset(conn, dataset_id)
            self._cache.pop(dataset_id, None)


def _expired(meta: dict) -> bool:
    exp = meta.get("expires_at")
    if not exp:
        return False
    try:
        return datetime.fromisoformat(str(exp).replace("Z", "+00:00")) < datetime.now(UTC)
    except ValueError:
        return False


@lru_cache(maxsize=1)
def get_repository() -> Repository:
    return Repository()
