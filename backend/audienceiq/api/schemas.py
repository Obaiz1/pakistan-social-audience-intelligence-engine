"""Pydantic contracts for the /api/v1 boundary (mirrored by frontend/lib/types.ts)."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Meta(BaseModel):
    dataset_id: str
    dataset_name: str
    mode: Literal["synthetic", "observed", "imported"]
    disclaimer: str
    text_permission: Literal["full", "illustrative", "withheld"]
    snapshot_at: str
    product_category: str | None = None
    run_id: str | None = None
    model_version: str | None = None
    sample_size: int | None = None
    filters: dict[str, Any] = {}
    generated_at: str
    assumptions: list[str] = []


class Envelope(BaseModel):
    model_config = ConfigDict(extra="allow")
    meta: Meta


class Health(BaseModel):
    status: Literal["ok", "degraded"]
    app: str
    version: str
    api_version: Literal["v1"]
    environment: str
    hosted: bool
    writes_enabled: bool
    llm_enabled: bool
    datasets: int
    default_dataset_id: str | None
    build_commit: str | None
    storage: dict[str, Any]
    time: str
    problems: list[str] = []


class Source(BaseModel):
    model_config = ConfigDict(extra="allow")
    source_id: str
    source_type: str
    name: str
    url: str | None = None
    collection_method: str
    collected_at: str | None = None
    reuse_permission: str
    notes: str | None = None


class DatasetSummary(BaseModel):
    dataset_id: str
    name: str
    mode: Literal["synthetic", "observed", "imported"]
    description: str | None = None
    product_category: str | None = None
    created_at: str
    snapshot_at: str
    expires_at: str | None = None
    expired: bool
    seed: int | None = None
    generator_version: str | None = None
    text_permission: Literal["full", "illustrative", "withheld"]
    disclaimer: str
    post_count: int
    comment_count: int
    builtin: bool
    sources: list[Source]


class DatasetList(BaseModel):
    datasets: list[DatasetSummary]
    default_dataset_id: str | None
    writes_enabled: bool


class Page(BaseModel):
    page: int
    page_size: int
    total: int
    pages: int


class ClusterProfile(BaseModel):
    model_config = ConfigDict(extra="allow")
    cluster_id: int
    label: str
    need_category: str
    label_source: str
    label_agreement: float
    size: int
    share: float
    filtered_size: int
    filtered_share: float
    cohesion: float | None
    top_terms: list[str]
    language_mix: dict[str, int]
    need_mix: dict[str, int]
    exemplars: list[dict[str, Any]]
    date_min: str | None
    date_max: str | None
    explanation: str


class AnomalyFlag(BaseModel):
    model_config = ConfigDict(extra="allow")
    flag_id: str
    post_id: str
    kind: Literal["engagement", "comment_pattern", "need_mix", "multivariate"]
    metric: str
    value: float | None
    baseline_median: float | None
    expected_low: float | None
    expected_high: float | None
    score: float
    iforest_score: float | None
    direction: Literal["positive", "negative"]
    cohort_key: str
    cohort_level: str
    cohort_size: int
    severity: Literal["high", "medium"]
    reason: str
    caveat: str


class Recommendation(BaseModel):
    recommendation_id: str
    title: str
    action_type: Literal["content", "promotion", "customer_service", "campaign_test", "investigation"]
    what_to_do: str
    why_it_matters: str
    audience_need: str | None
    where: dict[str, Any]
    linked_evidence: list[dict[str, Any]]
    priority: int = Field(ge=1, le=3)
    evidence_strength: Literal["strong", "moderate", "limited"]
    sample_size: int
    metrics: dict[str, Any]
    limitations: list[str]
    test_plan: str
    generated_at: str


class ImportPreviewRequest(BaseModel):
    posts_csv: str | None = Field(default=None, max_length=4_000_000)
    comments_csv: str | None = Field(default=None, max_length=4_000_000)
    posts_mapping: dict[str, str | None] | None = None
    comments_mapping: dict[str, str | None] | None = None


class Attestation(BaseModel):
    source_description: str = Field(min_length=5, max_length=500)
    collected_at: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    permission_confirmed: bool
    data_kind: Literal["observed", "synthetic"]
    source_url: str | None = Field(default=None, max_length=500)


class ImportConfirmRequest(ImportPreviewRequest):
    name: str = Field(min_length=3, max_length=80)
    product_category: str = Field(default="Women's lawn suits", max_length=80)
    attestation: Attestation


class DemoRequest(BaseModel):
    n_posts: int = Field(default=600, ge=100, le=5000)
    seed: int = Field(default=42, ge=0, le=1_000_000)
