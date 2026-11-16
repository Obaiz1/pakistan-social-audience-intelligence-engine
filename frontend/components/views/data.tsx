"use client";

import { CheckCircle2, Download, Upload, XCircle } from "lucide-react";
import { Fragment, useState } from "react";
import { API, deleteJson, errorText, postJson, useApi } from "@/lib/api";
import { MODE_LABEL, date, num, pct } from "@/lib/format";
import type { Meta } from "@/lib/types";
import { useDataset } from "../dataset";
import { Busy, ErrorState, Kpi, LoadingPage, ModeBadge, Notice, PageHead, Panel } from "../ui";

type Quality = {
  meta: Meta;
  checks: { check: string; passed: boolean; detail: string; severity: string }[];
  passed: boolean;
  posts: { total: number; platforms: Record<string, number>; brands: Record<string, number>; content_types: Record<string, number>; campaigns: number; date_min: string; date_max: string; missing: Record<string, { missing: number; share: number; zeros: number | null }> };
  comments: { total: number; posts_with_comments: number; text_permission: string; languages: Record<string, number>; median_chars: number | null };
  provenance: { mode: string; disclaimer: string; snapshot_at: string; expires_at: string | null; seed: number | null; generator_version: string | null };
  pipeline: { step: string; status: string }[];
};
type Side = { rows_read: number; rows_valid: number; error_count: number; errors: { row: number | null; field: string; message: string }[]; warnings: string[]; columns: string[]; mapping: Record<string, string | null>; fields: Record<string, { required: boolean }>; sample: Record<string, unknown>[] };
type Preview = { posts: Side | null; comments: Side | null; ready: boolean; ready_reason?: string };

async function readFile(f: File | null): Promise<string | null> {
  if (!f) return null;
  if (f.size > 2 * 1024 * 1024) throw new Error(`${f.name} is larger than the 2 MB upload limit.`);
  return await f.text();
}

function MappingEditor({ side, value, onChange, kind }: { side: Side; value: Record<string, string | null>; onChange: (m: Record<string, string | null>) => void; kind: string }) {
  return (
    <div className="grid cols-3">
      {Object.entries(side.fields).map(([field, spec]) => (
        <label key={field} className="field">{field}{spec.required ? " *" : ""}
          <select className="select" value={value[field] ?? ""} onChange={(e) => onChange({ ...value, [field]: e.target.value || null })} aria-label={`${kind} field ${field}`}>
            <option value="">— not mapped —</option>
            {side.columns.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </label>
      ))}
    </div>
  );
}

function SideReport({ title, side }: { title: string; side: Side }) {
  return (
    <div className="stack">
      <div className="row"><strong>{title}</strong><span className="badge num">{num(side.rows_valid)} / {num(side.rows_read)} valid</span>{side.error_count > 0 && <span className="badge critical">{side.error_count} errors</span>}</div>
      {side.warnings.map((w) => <Notice key={w} tone="warn">{w}</Notice>)}
      {side.errors.length > 0 && (
        <div className="table-wrap"><table className="data"><thead><tr><th>Row</th><th>Field</th><th>Problem</th></tr></thead>
          <tbody>{side.errors.slice(0, 12).map((e, i) => <tr key={i}><td className="num">{e.row ?? "—"}</td><td className="mono">{e.field}</td><td>{e.message}</td></tr>)}</tbody></table></div>
      )}
      {side.sample.length > 0 && (
        <div className="table-wrap"><table className="data"><thead><tr>{Object.keys(side.sample[0]).slice(0, 8).map((k) => <th key={k}>{k}</th>)}</tr></thead>
          <tbody>{side.sample.slice(0, 5).map((r, i) => <tr key={i}>{Object.keys(side.sample[0]).slice(0, 8).map((k) => <td key={k} className="bidi">{r[k] === null ? <span className="faint">null</span> : String(r[k]).slice(0, 60)}</td>)}</tr>)}</tbody></table></div>
      )}
    </div>
  );
}

function ImportWizard() {
  const { writesEnabled, refresh, select } = useDataset();
  const [postsFile, setPostsFile] = useState<File | null>(null);
  const [commentsFile, setCommentsFile] = useState<File | null>(null);
  const [texts, setTexts] = useState<{ posts: string | null; comments: string | null }>({ posts: null, comments: null });
  const [preview, setPreview] = useState<Preview | null>(null);
  const [pmap, setPmap] = useState<Record<string, string | null>>({});
  const [cmap, setCmap] = useState<Record<string, string | null>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);
  const [att, setAtt] = useState({ name: "", source_description: "", collected_at: "", permission_confirmed: false, data_kind: "observed" as "observed" | "synthetic", source_url: "" });

  const runPreview = async (pm?: Record<string, string | null>, cm?: Record<string, string | null>) => {
    setBusy("Validating…"); setError(null); setDone(null);
    try {
      const posts = texts.posts ?? (await readFile(postsFile));
      const comments = texts.comments ?? (await readFile(commentsFile));
      setTexts({ posts, comments });
      const res = await postJson<Preview>("/imports/preview", { posts_csv: posts, comments_csv: comments, posts_mapping: pm ?? null, comments_mapping: cm ?? null });
      setPreview(res);
      if (res.posts) setPmap(res.posts.mapping);
      if (res.comments) setCmap(res.comments.mapping);
    } catch (e) { setError(errorText(e)); } finally { setBusy(null); }
  };
  const confirm = async () => {
    setBusy("Running the full pipeline (clustering, anomalies, recommendations)…"); setError(null);
    try {
      const res = await postJson<{ dataset_id: string; posts: number; comments: number; clusters: number; warnings: string[] }>("/imports/confirm", {
        posts_csv: texts.posts, comments_csv: texts.comments, posts_mapping: pmap, comments_mapping: cmap, name: att.name,
        attestation: { source_description: att.source_description, collected_at: att.collected_at, permission_confirmed: att.permission_confirmed, data_kind: att.data_kind, source_url: att.source_url || null },
      });
      setDone(`Imported ${num(res.posts)} posts and ${num(res.comments)} comments into ${res.dataset_id} (${res.clusters} clusters).`);
      await refresh();
      select(res.dataset_id);
    } catch (e) { setError(errorText(e)); } finally { setBusy(null); }
  };
  const attOk = att.name.length >= 3 && att.source_description.length >= 5 && /^\d{4}-\d{2}-\d{2}$/.test(att.collected_at) && att.permission_confirmed;

  return (
    <Panel id="import" title="Import your own CSV export" description="Upload a posts file and a comments file exported from accounts you own or are authorised to analyse. Step 1 validates without saving anything.">
      <div className="stack">
        <div className="row">
          <a className="btn sm" href={`${API}/imports/templates/posts`}><Download size={14} /> Posts template</a>
          <a className="btn sm" href={`${API}/imports/templates/comments`}><Download size={14} /> Comments template</a>
          <span className="faint">CSV, UTF-8, ≤ 2 MB each. Username/author columns are dropped automatically and never stored.</span>
        </div>
        <div className="grid cols-2">
          <label className="field">Posts CSV<input className="input" type="file" accept=".csv,text/csv" onChange={(e) => { setPostsFile(e.target.files?.[0] ?? null); setTexts((t) => ({ ...t, posts: null })); setPreview(null); }} /></label>
          <label className="field">Comments CSV<input className="input" type="file" accept=".csv,text/csv" onChange={(e) => { setCommentsFile(e.target.files?.[0] ?? null); setTexts((t) => ({ ...t, comments: null })); setPreview(null); }} /></label>
        </div>
        <div className="btn-row"><button className="btn primary" type="button" disabled={(!postsFile && !commentsFile) || !!busy} onClick={() => runPreview()}><Upload size={15} /> 1 · Preview &amp; validate</button></div>
        {busy && <Busy text={busy} />}
        {error && <Notice tone="error" title="Import problem">{error}</Notice>}
        {done && <Notice tone="ok" title="Import complete">{done}</Notice>}
        {preview && (
          <>
            {preview.posts && (<Panel flat title="2 · Map post fields" description="Suggested from your column names; adjust and re-validate."><MappingEditor side={preview.posts} value={pmap} onChange={setPmap} kind="Posts" /></Panel>)}
            {preview.comments && (<Panel flat title="Map comment fields"><MappingEditor side={preview.comments} value={cmap} onChange={setCmap} kind="Comments" /></Panel>)}
            <div className="btn-row"><button className="btn" type="button" disabled={!!busy} onClick={() => runPreview(pmap, cmap)}>Re-validate with this mapping</button></div>
            <Panel flat title="3 · Validation report">
              <div className="grid cols-2">{preview.posts && <SideReport title="Posts" side={preview.posts} />}{preview.comments && <SideReport title="Comments" side={preview.comments} />}</div>
              <div style={{ marginTop: 10 }}>{preview.ready ? <Notice tone="ok" title="Ready to import">Enough valid, joined rows for an analysis.</Notice> : <Notice tone="warn" title="Not ready">{preview.ready_reason}</Notice>}</div>
            </Panel>
            <Panel flat title="4 · Source attestation" description="Required before anything is stored. Imported data is labelled 'Imported' everywhere it appears.">
              <div className="grid cols-2">
                <label className="field">Dataset name<input className="input" value={att.name} onChange={(e) => setAtt({ ...att, name: e.target.value })} maxLength={80} /></label>
                <label className="field">Collection date<input className="input" type="date" value={att.collected_at} onChange={(e) => setAtt({ ...att, collected_at: e.target.value })} /></label>
                <label className="field span-2">Where did this data come from?<textarea className="input" value={att.source_description} onChange={(e) => setAtt({ ...att, source_description: e.target.value })} maxLength={500} placeholder="e.g. Instagram Insights export of our brand account, Oct 2026" /></label>
                <label className="field">Source URL (optional)<input className="input" value={att.source_url} onChange={(e) => setAtt({ ...att, source_url: e.target.value })} maxLength={500} /></label>
                <label className="field">Data kind<select className="select" value={att.data_kind} onChange={(e) => setAtt({ ...att, data_kind: e.target.value as "observed" | "synthetic" })}><option value="observed">Observed (real export)</option><option value="synthetic">Synthetic / simulated</option></select></label>
              </div>
              <label className="row" style={{ marginTop: 10, fontSize: 13.5 }}><input type="checkbox" checked={att.permission_confirmed} onChange={(e) => setAtt({ ...att, permission_confirmed: e.target.checked })} /> I am allowed to use and store this data for analysis, and it contains no data I am not permitted to process.</label>
              {!writesEnabled && <Notice tone="warn" title="Read-only public demo">This hosted demo does not store imports (no durable database is attached). Preview and validation above work here; run the app locally (README → Local setup) to import and analyse your file.</Notice>}
              <div className="btn-row" style={{ marginTop: 10 }}>
                <button className="btn primary" type="button" disabled={!preview.ready || !attOk || !writesEnabled || !!busy} onClick={confirm}>5 · Confirm import &amp; analyse</button>
              </div>
            </Panel>
          </>
        )}
      </div>
    </Panel>
  );
}

function DemoGenerator() {
  const { writesEnabled, refresh, select } = useDataset();
  const [n, setN] = useState(600);
  const [seed, setSeed] = useState(42);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ tone: "ok" | "error"; text: string } | null>(null);
  return (
    <Panel title="Synthetic demo generator" description="Regenerate a labelled synthetic corpus with any seed. The shipped seed-42 demo uses offline semantic embeddings; regenerated corpora use the runtime lexical baseline.">
      <div className="row">
        <label className="field">Posts<input className="input" type="number" min={100} max={5000} value={n} onChange={(e) => setN(Number(e.target.value))} /></label>
        <label className="field">Seed<input className="input" type="number" min={0} value={seed} onChange={(e) => setSeed(Number(e.target.value))} /></label>
        <button className="btn" type="button" disabled={!writesEnabled || busy} style={{ alignSelf: "flex-end" }} onClick={async () => {
          setBusy(true); setMsg(null);
          try {
            const r = await postJson<{ dataset_id: string; posts: number; comments: number }>("/datasets/demo", { n_posts: n, seed });
            setMsg({ tone: "ok", text: `Generated ${r.dataset_id}: ${num(r.posts)} posts, ${num(r.comments)} comments.` });
            await refresh(); select(r.dataset_id);
          } catch (e) { setMsg({ tone: "error", text: errorText(e) }); } finally { setBusy(false); }
        }}>Generate</button>
      </div>
      {busy && <Busy text="Generating and analysing…" />}
      {msg && <div style={{ marginTop: 8 }}><Notice tone={msg.tone}>{msg.text}</Notice></div>}
      {!writesEnabled && <div style={{ marginTop: 8 }}><Notice tone="info">Disabled on the public demo so visitors cannot overwrite shared data. Locally: <code>POST /api/v1/datasets/demo</code>.</Notice></div>}
    </Panel>
  );
}

export function DataView() {
  const { datasets, datasetId, select, writesEnabled, refresh, health } = useDataset();
  const q = useApi<Quality>(datasetId ? "/data/quality" : null, { dataset_id: datasetId });
  return (
    <div className="grid">
      <PageHead eyebrow="Data" title="Datasets, provenance and imports">
        Observed, imported and synthetic records are never merged. Each dataset carries its source, collection method, reuse permission and snapshot date; observed API data expires after 30 days unless refreshed.
      </PageHead>
      <Panel title="Available datasets" description={health?.hosted ? "Public read-only demo." : "Local mode: imported datasets are stored in var/audienceiq_user.sqlite (git-ignored)."}>
        <div className="grid cols-2">
          {datasets.map((d) => (
            <article key={d.dataset_id} className="rec" aria-label={d.name}>
              <div className="row"><ModeBadge mode={d.mode} />{d.expired && <span className="badge critical">expired</span>}{d.dataset_id === datasetId && <span className="badge accent">selected</span>}<span className="faint mono" style={{ marginLeft: "auto" }}>{d.dataset_id}</span></div>
              <h3>{d.name}</h3>
              <p className="why">{d.description}</p>
              <dl className="kv">
                <dt>Records</dt><dd className="num">{num(d.post_count)} posts · {num(d.comment_count)} comments</dd>
                <dt>Snapshot</dt><dd>{date(d.snapshot_at)}{d.expires_at && ` · expires ${date(d.expires_at)}`}</dd>
                <dt>Comment text</dt><dd>{d.text_permission}</dd>
                {d.seed !== null && <><dt>Seed</dt><dd className="num">{d.seed} · {d.generator_version}</dd></>}
                {d.sources.map((s) => <Fragment key={s.source_id}><dt>Source</dt><dd>{s.name} — {s.collection_method}. <span className="faint">{s.reuse_permission}</span></dd></Fragment>)}
              </dl>
              <div className="btn-row">
                <button className="btn sm" type="button" disabled={d.dataset_id === datasetId || d.expired} onClick={() => select(d.dataset_id)}>Use this dataset</button>
                {!d.builtin && writesEnabled && <button className="btn sm ghost" type="button" onClick={async () => { await deleteJson(`/datasets/${d.dataset_id}`); await refresh(); }}>Delete</button>}
              </div>
            </article>
          ))}
        </div>
        <p className="faint" style={{ marginTop: 10 }}>Modes: {Object.values(MODE_LABEL).join(" · ")}. Instagram, TikTok and Facebook have no live connector here; their data can only enter through an authorised CSV export.</p>
      </Panel>
      {q.loading && <LoadingPage />}
      {q.error && <ErrorState error={q.error} status={q.status} onRetry={q.reload} />}
      {q.data && (
        <Panel title={`Quality audit · ${q.data.meta.dataset_name}`} description="Checks run against the selected dataset as served.">
          <div className="grid cols-4">
            <Kpi label="Posts" value={num(q.data.posts.total)} sub={`${q.data.posts.date_min} → ${q.data.posts.date_max}`} />
            <Kpi label="Comments" value={num(q.data.comments.total)} sub={`on ${num(q.data.comments.posts_with_comments)} posts`} />
            <Kpi label="Campaigns" value={num(q.data.posts.campaigns)} sub={`${Object.keys(q.data.posts.brands).length} brands`} />
            <Kpi label="Checks" value={q.data.passed ? "Passed" : "Issues"} sub={`${q.data.checks.filter((c) => c.passed).length}/${q.data.checks.length} passed`} />
          </div>
          <div className="grid cols-2" style={{ marginTop: 14 }}>
            <div className="table-wrap"><table className="data"><thead><tr><th>Check</th><th>Result</th></tr></thead>
              <tbody>{q.data.checks.map((c) => <tr key={c.check}><td>{c.check}</td><td>{c.passed ? <span className="row" style={{ gap: 6 }}><CheckCircle2 size={15} color="var(--ok)" aria-hidden="true" /> pass <span className="faint">{c.detail}</span></span> : <span className="row" style={{ gap: 6 }}><XCircle size={15} color={c.severity === "error" ? "var(--critical)" : "var(--amber)"} aria-hidden="true" /> {c.severity} <span className="faint">{c.detail}</span></span>}</td></tr>)}</tbody></table></div>
            <div className="table-wrap"><table className="data"><thead><tr><th>Post field</th><th className="n">Missing</th><th className="n">Zeros</th></tr></thead>
              <tbody>{Object.entries(q.data.posts.missing).map(([f, m]) => <tr key={f}><td className="mono">{f}</td><td className="n">{num(m.missing)} ({pct(m.share, 0)})</td><td className="n">{m.zeros === null ? "—" : num(m.zeros)}</td></tr>)}</tbody></table>
              <p className="faint" style={{ padding: "8px 10px" }}>Missing = not reported by the platform/export (kept null). Zeros are real zeros.</p></div>
          </div>
        </Panel>
      )}
      <DemoGenerator />
      <ImportWizard />
    </div>
  );
}
