"""Shared API helpers: dataset resolution, filters, the response `meta` envelope and JSON-safe conversion."""

import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime

import numpy as np
import pandas as pd
from fastapi import HTTPException, Query

from audienceiq.analytics.engagement import apply_filters
from audienceiq.constants import CONTENT_TYPES, PLATFORMS
from audienceiq.storage.repository import DatasetExpired, DatasetFrames, DatasetNotFound, get_repository


@dataclass
class Filters:
    platform: list[str]
    brand: list[str]
    campaign: list[str]
    content_type: list[str]
    date_from: str | None
    date_to: str | None

    def as_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v}

    @property
    def active(self) -> bool:
        return bool(self.as_dict())


def filters_dep(
    platform: list[str] = Query(default=[]), brand: list[str] = Query(default=[]),
    campaign: list[str] = Query(default=[]), content_type: list[str] = Query(default=[]),
    date_from: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    date_to: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
) -> Filters:
    bad = [p for p in platform if p not in PLATFORMS] + [c for c in content_type if c not in CONTENT_TYPES]
    if bad:
        raise HTTPException(422, f"Unknown filter value(s): {', '.join(bad)}")
    if date_from and date_to and date_from > date_to:
        raise HTTPException(422, "date_from must be on or before date_to")
    return Filters(platform, brand, campaign, content_type, date_from, date_to)


def load_frames(dataset_id: str | None) -> DatasetFrames:
    repo = get_repository()
    ds = dataset_id or repo.default_dataset_id()
    if not ds:
        raise HTTPException(404, "No dataset is available. Build the demo dataset with `python pipelines/build_demo.py`.")
    try:
        return repo.frames(ds)
    except DatasetNotFound:
        raise HTTPException(404, f"Dataset '{ds}' not found.") from None
    except DatasetExpired:
        raise HTTPException(410, f"Dataset '{ds}' has expired (observed API data must be refreshed or deleted within "
                                 "30 days). Re-run the collection pipeline to refresh it.") from None


def filtered_posts(f: DatasetFrames, filters: Filters) -> pd.DataFrame:
    return apply_filters(f.posts, filters.as_dict())


def meta(f: DatasetFrames, sample_size: int | None = None, filters: Filters | None = None, run: dict | None = None,
         assumptions: list[str] | None = None, model_version: str | None = None) -> dict:
    m = f.meta
    return {
        "dataset_id": m["dataset_id"], "dataset_name": m["name"], "mode": m["mode"], "disclaimer": m["disclaimer"],
        "text_permission": m["text_permission"], "snapshot_at": m["snapshot_at"], "product_category": m["product_category"],
        "run_id": (run or {}).get("run_id"), "model_version": model_version or (run or {}).get("model_version"),
        "sample_size": sample_size, "filters": filters.as_dict() if filters else {},
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"), "assumptions": assumptions or [],
    }


def clean(obj):
    """Recursively convert numpy/pandas scalars and NaN/inf to JSON-safe values."""
    if isinstance(obj, dict):
        return {str(k): clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [clean(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        v = float(obj)
        return None if math.isnan(v) or math.isinf(v) else round(v, 6)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if obj is pd.NA or obj is pd.NaT:
        return None
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    return obj


def frame_records(df: pd.DataFrame, cols: list[str] | None = None) -> list[dict]:
    if df is None or df.empty:
        return []
    d = df[cols] if cols else df
    return [clean(r) for r in d.astype(object).where(pd.notna(d), None).to_dict(orient="records")]


def loads(value, default=None):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return default
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


def paginate(df: pd.DataFrame, page: int, page_size: int) -> tuple[pd.DataFrame, dict]:
    total = int(len(df))
    pages = max(1, math.ceil(total / page_size))
    page = min(max(1, page), pages)
    start = (page - 1) * page_size
    return df.iloc[start:start + page_size], {"page": page, "page_size": page_size, "total": total, "pages": pages}
