"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useApi } from "@/lib/api";
import { ACTION_LABEL, CONTENT_LABEL, NEED_LABEL, label, num } from "@/lib/format";
import { STATUSES, STATUS_LABEL, parseStatuses, storageKey, withStatus, type Status } from "@/lib/status";
import type { Evidence, Meta, Recommendation } from "@/lib/types";
import { useDataset } from "../dataset";
import { useFilters } from "../filters";
import { QuestionStepper } from "../story";
import { useToast } from "../toast";
import { Empty, ErrorState, LoadingPage, MethodNote, Notice, PageHead, Panel, Segmented } from "../ui";

type Resp = { meta: Meta; llm_wording_enabled: boolean; recommendations: Recommendation[]; counts: { by_action: Record<string, number>; by_priority: Record<string, number> } };

function EvidenceLink({ e }: { e: Evidence }) {
  if (e.type === "cluster") return <Link className="chip" href={`/audience?cluster=${e.id}`}>Cluster #{e.id} · {e.label} · {num(e.size ?? 0)} comments</Link>;
  if (e.type === "anomaly") return <Link className="chip mono" href={`/anomalies?flag=${e.id}`}>{e.post_id}</Link>;
  if (e.type === "need_concentration") {
    const href = e.dimension === "campaign" ? `/campaigns` : e.dimension === "brand" ? `/segments?brand=${encodeURIComponent(String(e.value))}` : e.dimension === "content_type" ? `/segments?content_type=${e.value}` : `/segments?platform=${e.value}`;
    return <Link className="chip" href={href}>{label(NEED_LABEL, e.need)} in {String(e.dimension).replace("_", " ")} “{e.dimension === "content_type" ? label(CONTENT_LABEL, String(e.value)) : e.value}” · {e.lift?.toFixed(2)}×</Link>;
  }
  if (e.type === "content_comparison") return <Link className="chip" href={`/content?content_type=${e.group}`}>Content comparison · {label(CONTENT_LABEL, e.group)}</Link>;
  return <span className="chip">{e.type}</span>;
}

function useStatuses(datasetId: string | null) {
  const [map, setMap] = useState<Record<string, Status>>({});
  useEffect(() => {
    if (!datasetId) return;
    let raw: string | null = null;
    try { raw = localStorage.getItem(storageKey(datasetId)); } catch { /* storage unavailable */ }
    // eslint-disable-next-line react-hooks/set-state-in-effect -- hydrate per-browser workflow state
    setMap(parseStatuses(raw));
  }, [datasetId]);
  const set = (id: string, status: Status) => {
    if (!datasetId) return;
    const next = withStatus(map, id, status);
    setMap(next);
    try { localStorage.setItem(storageKey(datasetId), JSON.stringify(next)); } catch { /* not persisted */ }
  };
  return { map, set };
}

export function RecCard({ r, status, onStatus }: { r: Recommendation; status?: Status; onStatus?: (s: Status) => void }) {
  const caveat = r.limitations.find((l) => !l.startsWith("SYNTHETIC")) ?? r.limitations[0];
  return (
    <article className="rec" id={r.recommendation_id} aria-labelledby={`${r.recommendation_id}-t`}>
      <div className="row">
        <span className="badge accent">Priority {r.priority}</span>
        <span className="badge">{label(ACTION_LABEL, r.action_type)}</span>
        <span className={`badge ${r.evidence_strength === "strong" ? "ok" : r.evidence_strength === "moderate" ? "" : "warn"}`}>{r.evidence_strength} evidence</span>
        {r.audience_need && <span className="badge">{label(NEED_LABEL, r.audience_need)}</span>}
        {onStatus && (
          <label style={{ marginLeft: "auto" }} className="row">
            <span className="sr-only">Workflow status for {r.title}</span>
            <select className="select" style={{ minHeight: 28, fontSize: 12 }} value={status ?? "new"} onChange={(e) => onStatus(e.target.value as Status)}>
              {STATUSES.map((s) => <option key={s} value={s}>{STATUS_LABEL[s]}</option>)}
            </select>
          </label>
        )}
      </div>
      <h3 id={`${r.recommendation_id}-t`}>{r.title}</h3>
      <dl className="opp">
        <dt>Opportunity</dt><dd>{r.what_to_do}</dd>
        <dt>Why it matters</dt><dd className="muted">{r.why_it_matters}</dd>
        <dt>Evidence</dt><dd className="row" style={{ gap: 6 }}>{r.linked_evidence.slice(0, 6).map((e, i) => <EvidenceLink key={i} e={e} />)}{r.linked_evidence.length > 6 && <span className="faint">+{r.linked_evidence.length - 6} more</span>}<span className="chip num">n = {num(r.sample_size)}</span></dd>
        <dt>Suggested test</dt><dd>{r.test_plan}</dd>
        <dt>Uncertainty</dt><dd className="faint">{caveat}</dd>
      </dl>
      <details>
        <summary>All numbers and limitations · <span className="mono">{r.recommendation_id}</span></summary>
        <ul>{Object.entries(r.metrics).map(([k, v]) => <li key={k}><span className="mono">{k}</span>: {String(v)}</li>)}</ul>
        <ul>{r.limitations.map((l) => <li key={l}>{l}</li>)}</ul>
        <p className="faint" style={{ marginTop: 6 }}>Where: {Object.entries(r.where).map(([k, v]) => `${k.replace("_", " ")} = ${v}`).join(", ")}</p>
      </details>
    </article>
  );
}

export function RecommendationsView() {
  const { datasetId } = useDataset();
  const { get, setParam } = useFilters();
  const toast = useToast();
  const action = get("action_type") ?? "";
  const priority = get("priority") ?? "";
  const statusFilter = get("status") ?? "";
  const s = useApi<Resp>(datasetId ? "/recommendations" : null, { dataset_id: datasetId, action_type: action, priority });
  const { map, set } = useStatuses(datasetId);
  const rows = (s.data?.recommendations ?? []).filter((r) => !statusFilter || (map[r.recommendation_id] ?? "new") === statusFilter);
  const counts = STATUSES.map((st) => ({ st, n: (s.data?.recommendations ?? []).filter((r) => (map[r.recommendation_id] ?? "new") === st).length }));
  return (
    <div className="grid">
      <QuestionStepper current={5} />
      <PageHead eyebrow="Question 5 · Action center" title="What should the marketing team do next?">
        Every card is generated from evidence that passed explicit gates — cluster support and name agreement, significant need concentrations, significant content effects, or recurring anomalies. If the evidence is not there, no card is produced. No sales or ROI predictions are made.
      </PageHead>
      <div className="row">
        <Segmented label="Action type" value={action} onChange={(v) => setParam("action_type", v || null)}
          options={[{ value: "", label: "All actions" }, ...Object.entries(ACTION_LABEL).map(([value, l]) => ({ value, label: l }))]} />
        <Segmented label="Priority" value={priority} onChange={(v) => setParam("priority", v || null)}
          options={[{ value: "", label: "Any priority" }, { value: "1", label: "P1" }, { value: "2", label: "P2" }, { value: "3", label: "P3" }]} />
        <Segmented label="Workflow status" value={statusFilter} onChange={(v) => setParam("status", v || null)}
          options={[{ value: "", label: "Any status" }, ...counts.map((c) => ({ value: c.st, label: `${STATUS_LABEL[c.st]} (${c.n})` }))]} />
      </div>
      {s.loading && <LoadingPage />}
      {s.error && <ErrorState error={s.error} status={s.status} onRetry={s.reload} />}
      {s.data && (
        <>
          <MethodNote meta={s.data.meta} extra={<><span className="chip">{s.data.llm_wording_enabled ? "AI wording available (numbers locked)" : "Deterministic wording (no AI)"}</span><span className="chip">Status saved in this browser only</span></>} />
          {s.data.meta.mode === "synthetic" && <Notice tone="warn" title="Synthetic demonstration">These actions demonstrate the method on simulated data. They are not findings about any real brand.</Notice>}
          {rows.length ? (
            <div className="grid cols-2">{rows.map((r) => <RecCard key={r.recommendation_id} r={r} status={map[r.recommendation_id]} onStatus={(st) => { set(r.recommendation_id, st); toast(`“${r.title}” marked ${STATUS_LABEL[st]}`); }} />)}</div>
          ) : <Panel><Empty title={statusFilter ? "No action has this status" : "No recommendation passed the evidence gates"}>{statusFilter ? "Change the status filter." : "Try removing filters, or see Methodology for the gate thresholds."}</Empty></Panel>}
        </>
      )}
    </div>
  );
}
