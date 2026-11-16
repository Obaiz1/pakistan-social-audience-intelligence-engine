/** Action-center workflow status, persisted per browser and dataset (the public server is read-only). Pure + testable. */

export const STATUSES = ["new", "review", "planned", "done"] as const;
export type Status = (typeof STATUSES)[number];
export const STATUS_LABEL: Record<Status, string> = { new: "New", review: "In review", planned: "Planned", done: "Done" };

export function storageKey(datasetId: string): string {
  return `audienceiq.actions.${datasetId}`;
}

export function parseStatuses(raw: string | null): Record<string, Status> {
  if (!raw) return {};
  try {
    const obj = JSON.parse(raw) as Record<string, unknown>;
    const out: Record<string, Status> = {};
    for (const [k, v] of Object.entries(obj)) if (typeof v === "string" && (STATUSES as readonly string[]).includes(v)) out[k] = v as Status;
    return out;
  } catch {
    return {};
  }
}

export function withStatus(map: Record<string, Status>, id: string, status: Status): Record<string, Status> {
  const next = { ...map };
  if (status === "new") delete next[id];
  else next[id] = status;
  return next;
}
