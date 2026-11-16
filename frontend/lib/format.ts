/** Display formatting. Missing values render as "N/A" — never as 0. */

export const NA = "N/A";

export function num(v: number | null | undefined, digits = 0): string {
  if (v === null || v === undefined || Number.isNaN(v)) return NA;
  return v.toLocaleString("en-PK", { maximumFractionDigits: digits, minimumFractionDigits: digits });
}

export function compact(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return NA;
  const a = Math.abs(v);
  if (a >= 1e6) return `${(v / 1e6).toFixed(a >= 1e7 ? 0 : 1)}M`;
  if (a >= 1e3) return `${(v / 1e3).toFixed(a >= 1e4 ? 0 : 1)}K`;
  return String(Math.round(v));
}

export function pct(v: number | null | undefined, digits = 1): string {
  if (v === null || v === undefined || Number.isNaN(v)) return NA;
  return `${(v * 100).toFixed(digits)}%`;
}

export function ratio(v: number | null | undefined, digits = 2): string {
  if (v === null || v === undefined || Number.isNaN(v)) return NA;
  return v.toFixed(digits);
}

export function pval(p: number | null | undefined): string {
  if (p === null || p === undefined || Number.isNaN(p)) return NA;
  if (p < 0.001) return "< 0.001";
  return p.toFixed(3);
}

export function date(iso: string | null | undefined): string {
  if (!iso) return NA;
  return iso.slice(0, 10);
}

export const CONTENT_LABEL: Record<string, string> = {
  reel: "Reel",
  video: "Video",
  product_photo: "Product photo",
  influencer_post: "Influencer post",
  styling_video: "Styling video",
  sale_announcement: "Sale announcement",
  other: "Other",
  unknown: "Unknown",
};

export const LANGUAGE_LABEL: Record<string, string> = {
  english: "English",
  roman_urdu: "Roman Urdu",
  urdu: "Urdu (script)",
  mixed: "Mixed",
  other: "Emoji / other",
  unknown: "Unknown",
};

export const NEED_LABEL: Record<string, string> = {
  price: "Price / cost",
  discount: "Discount & sale",
  delivery: "Delivery & shipping",
  availability: "Availability & stock",
  size_fit: "Size & fit",
  fabric_quality: "Fabric & quality",
  purchase_inquiry: "Purchase / inbox inquiry",
  order_issue: "Order problem",
  compliment: "Compliments",
  other: "Other / unclear",
  mixed: "Mixed",
  noise: "Unclustered",
};

export const ACTION_LABEL: Record<string, string> = {
  content: "Content",
  promotion: "Promotion",
  customer_service: "Customer service",
  campaign_test: "Campaign test",
  investigation: "Investigate",
};

export const KIND_LABEL: Record<string, string> = {
  engagement: "Engagement outlier",
  comment_pattern: "Comment pattern",
  need_mix: "Need-mix shift",
  multivariate: "Multivariate (Isolation Forest)",
};

export const MODE_LABEL: Record<string, string> = {
  synthetic: "Synthetic demo",
  observed: "Observed",
  imported: "Imported",
};

export function label(map: Record<string, string>, key: string | null | undefined): string {
  if (!key) return NA;
  return map[key] ?? key.replace(/_/g, " ");
}

export function metricValue(metric: string, v: number | null | undefined): string {
  if (metric === "er_views") return pct(v, 2);
  if (metric === "interactions") return num(v);
  if (metric === "isolation_forest") return ratio(v, 3);
  if (metric.startsWith("share:")) return pct(v, 0);
  return ratio(v, 3);
}

/** Heat-cell opacity for a share in [0, 1]. Capped at 0.72 so cell text keeps ≥ 4.5:1 contrast in both themes (axe-checked). */
export const HEAT_MAX_ALPHA = 0.72;
export function heatAlpha(share: number | null | undefined): number {
  if (!share || share < 0) return 0;
  return Math.min(HEAT_MAX_ALPHA, share * 2.2);
}
