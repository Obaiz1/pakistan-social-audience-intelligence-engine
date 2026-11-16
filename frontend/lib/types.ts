/**
 * Typed mirror of the FastAPI /api/v1 contracts (backend/audienceiq/api/schemas.py).
 * The backend is the single source of numeric truth; the frontend never recomputes metrics.
 */

export type Mode = "synthetic" | "observed" | "imported";
export type TextPermission = "full" | "illustrative" | "withheld";
export type Num = number | null;

export interface Meta {
  dataset_id: string;
  dataset_name: string;
  mode: Mode;
  disclaimer: string;
  text_permission: TextPermission;
  snapshot_at: string;
  product_category: string | null;
  run_id: string | null;
  model_version: string | null;
  sample_size: number | null;
  filters: Record<string, string[] | string>;
  generated_at: string;
  assumptions: string[];
}

export interface Source {
  source_id: string;
  source_type: string;
  name: string;
  url: string | null;
  collection_method: string;
  collected_at: string | null;
  reuse_permission: string;
  notes: string | null;
}

export interface DatasetSummary {
  dataset_id: string;
  name: string;
  mode: Mode;
  description: string | null;
  product_category: string | null;
  created_at: string;
  snapshot_at: string;
  expires_at: string | null;
  expired: boolean;
  seed: number | null;
  generator_version: string | null;
  text_permission: TextPermission;
  disclaimer: string;
  post_count: number;
  comment_count: number;
  builtin: boolean;
  sources: Source[];
}

export interface DatasetList {
  datasets: DatasetSummary[];
  default_dataset_id: string | null;
  writes_enabled: boolean;
}

export interface Health {
  status: "ok" | "degraded";
  app: string;
  version: string;
  environment: string;
  hosted: boolean;
  writes_enabled: boolean;
  llm_enabled: boolean;
  datasets: number;
  default_dataset_id: string | null;
  build_commit: string | null;
  time: string;
  problems: string[];
}

export interface Option {
  value: string | number;
  label: string;
}

export interface Options {
  meta: Meta;
  platforms: string[];
  brands: string[];
  campaigns: string[];
  content_types: Option[];
  languages: Option[];
  topics: Option[];
  clusters: Option[];
  date_min: string;
  date_max: string;
}

export interface PageInfo {
  page: number;
  page_size: number;
  total: number;
  pages: number;
}

export interface Post {
  post_id: string;
  brand: string;
  platform: string;
  campaign: string;
  content_type: string;
  product_category: string;
  likes: Num;
  comments_count: Num;
  shares: Num;
  views: Num;
  days_since_post: number;
  published_at: string;
  interactions: Num;
  er_views: Num;
  er_formula: string;
  attention_index: Num;
  mature: boolean;
  source_url: string | null;
  source_type: string;
  observed_vs_synthetic: string;
  flagged?: boolean;
}

export interface CompareRow {
  group: string;
  label: string;
  n: number;
  median: Num;
  rest_median: Num;
  ci_low: Num;
  ci_high: Num;
  sufficient: boolean;
  p_value: Num;
  p_adj: Num;
  significant: boolean | null;
  cliffs_delta: Num;
  effect: string;
  posts_total: number;
  posts_mature: number;
  weighted_er: Num;
}

export interface Comparison {
  dimension: string;
  metric: string;
  metric_help: string;
  min_n: number;
  kruskal_p: Num;
  posts_compared: number;
  posts_excluded_immature: number;
  rows: CompareRow[];
}

export interface ClusterProfile {
  cluster_id: number;
  label: string;
  need_category: string;
  need_label: string;
  label_source: string;
  label_agreement: number;
  size: number;
  share: number;
  filtered_size: number;
  filtered_share: number;
  cohesion: Num;
  top_terms: string[];
  language_mix: Record<string, number>;
  need_mix: Record<string, number>;
  exemplars: { comment_id: string; language_type: string; text: string | null; similarity: Num }[];
  date_min: string | null;
  date_max: string | null;
  explanation: string;
}

export interface AnomalyFlag {
  flag_id: string;
  post_id: string;
  kind: "engagement" | "comment_pattern" | "need_mix" | "multivariate";
  metric: string;
  value: Num;
  baseline_median: Num;
  expected_low: Num;
  expected_high: Num;
  score: number;
  iforest_score: Num;
  direction: "positive" | "negative";
  cohort_key: string;
  cohort_level: string;
  cohort_size: number;
  severity: "high" | "medium";
  reason: string;
  caveat: string;
  brand?: string;
  platform?: string;
  content_type?: string;
  campaign?: string;
  published_at?: string;
  source_url?: string | null;
}

export interface Evidence {
  type: "cluster" | "anomaly" | "need_concentration" | "content_comparison";
  id?: string | number;
  label?: string;
  size?: number;
  post_id?: string;
  dimension?: string;
  value?: string;
  need?: string;
  lift?: number;
  group?: string;
}

export interface Recommendation {
  recommendation_id: string;
  title: string;
  action_type: "content" | "promotion" | "customer_service" | "campaign_test" | "investigation";
  what_to_do: string;
  why_it_matters: string;
  audience_need: string | null;
  audience_need_label: string | null;
  where: Record<string, string>;
  linked_evidence: Evidence[];
  priority: 1 | 2 | 3;
  evidence_strength: "strong" | "moderate" | "limited";
  sample_size: number;
  metrics: Record<string, number | string | null>;
  limitations: string[];
  test_plan: string;
  generated_at: string;
}

export interface CommentRow {
  comment_id: string;
  post_id: string;
  comment_text: string | null;
  language_type: string;
  topic: string;
  topic_confidence?: Num;
  sentiment: string;
  purchase_intent: string;
  cluster_id: number | null;
  cluster_label: string | null;
  need: string | null;
  published_at: string | null;
  platform?: string;
  brand?: string;
  campaign?: string;
  content_type?: string;
  distance?: Num;
}

export interface NeedShare {
  need: string;
  share: number;
  lift: number;
}

export interface NeedsBy {
  campaign?: string;
  platform?: string;
  comments: number;
  sufficient: boolean;
  needs: NeedShare[];
}
