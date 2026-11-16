"use client";

import { FileSpreadsheet, FileText, FileType } from "lucide-react";
import { exportUrl } from "@/lib/api";
import { countActive } from "@/lib/query";
import { useDataset } from "../dataset";
import { FilterBar, useFilters } from "../filters";
import { ModeBadge, Notice, PageHead, Panel } from "../ui";

const SECTIONS = [
  { id: "summary", label: "Summary", desc: "Dataset, provenance, model run and counts." },
  { id: "posts", label: "Posts", desc: "Posts with platform-specific engagement metrics." },
  { id: "comments", label: "Comments", desc: "Comments with language, reference topic, intent and cluster (text omitted when withheld)." },
  { id: "clusters", label: "Clusters", desc: "Cluster profiles: size, share, terms, language mix, explanation." },
  { id: "anomalies", label: "Anomalies", desc: "Flags with cohort, baseline, score, reason and caveat." },
  { id: "recommendations", label: "Recommendations", desc: "Cards with evidence, limitations and test plans." },
];

export function ReportsView() {
  const { datasetId, dataset } = useDataset();
  const { filters } = useFilters();
  const base = { dataset_id: datasetId, ...filters };
  return (
    <div className="grid">
      <PageHead eyebrow="Deliverables" title="Reports & exports">
        Download what you see. Every export repeats the dataset disclaimer and provenance, applies the current filters to post-level sections, and guards against spreadsheet formula injection.
      </PageHead>
      <FilterBar />
      {dataset && (
        <Notice tone={dataset.mode === "synthetic" ? "warn" : "info"} title="Data-source disclosure">
          <span className="row" style={{ gap: 8 }}><ModeBadge mode={dataset.mode} /> {dataset.disclaimer}</span>
          <span className="faint">{dataset.sources.map((s) => `${s.name}: ${s.reuse_permission}`).join(" · ")}{countActive(filters) ? " · Filters applied to posts, comments and anomalies." : ""}</span>
        </Notice>
      )}
      <div className="grid cols-2">
        <Panel title="Full workbook (Excel)" description="All sections as sheets plus a README sheet with the disclaimer.">
          <a className="btn primary" href={exportUrl({ ...base, format: "xlsx" })}><FileSpreadsheet size={16} /> Download .xlsx</a>
        </Panel>
        <Panel title="Summary report (PDF)" description="One-page-per-section summary of Q1–Q5 findings with limitations. Urdu-script text is omitted from the PDF (font); use CSV/Excel for full text.">
          <a className="btn primary" href={exportUrl({ ...base, format: "pdf" })}><FileType size={16} /> Download .pdf</a>
        </Panel>
      </div>
      <Panel title="CSV by section" description="UTF-8 with BOM (opens correctly in Excel, including Urdu).">
        <div className="table-wrap"><table className="data"><thead><tr><th>Section</th><th>Contents</th><th>Download</th></tr></thead>
          <tbody>{SECTIONS.map((s) => (
            <tr key={s.id}><td><strong>{s.label}</strong></td><td className="faint">{s.desc}</td>
              <td><a className="btn sm" href={exportUrl({ ...base, format: "csv", section: s.id })}><FileText size={14} /> CSV</a></td></tr>
          ))}</tbody></table></div>
      </Panel>
      <p className="faint">Methodology notes and reproducibility commands are on the Methodology page and in the repository&apos;s docs/ folder.</p>
    </div>
  );
}
