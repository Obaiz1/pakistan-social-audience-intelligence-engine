"use client";

import Link from "next/link";
import { num, pct } from "@/lib/format";

export type NeedGroup = {
  need: string;
  label: string;
  comments: number;
  share: number;
  uncertain: boolean;
  clusters: { cluster_id: number; label: string; size: number; agreement: number }[];
};

/** Discovered needs as ranked bars. Mixed/noise stay visible (striped) — uncertainty is never relabelled away. */
export function NeedsDistribution({ needs, onSelect, hrefFor, total }: {
  needs: NeedGroup[];
  total: number;
  onSelect?: (clusterId: number) => void;
  hrefFor?: (g: NeedGroup) => string;
}) {
  const max = Math.max(...needs.map((n) => n.comments), 1);
  return (
    <div className="needs" role="list" aria-label="Discovered audience needs">
      {needs.map((g) => {
        const top = [...g.clusters].sort((a, b) => b.size - a.size)[0];
        const agree = g.clusters.reduce((s, c) => s + c.agreement * c.size, 0) / Math.max(1, g.clusters.reduce((s, c) => s + c.size, 0));
        const inner = (
          <>
            <span className="name">
              {g.label}
              {g.uncertain && <span className="badge warn">uncertain</span>}
              {g.clusters.length > 1 && <span className="faint">· {g.clusters.length} clusters</span>}
            </span>
            <span className="bar" aria-hidden="true"><span style={{ width: `${(100 * g.comments) / max}%` }} /></span>
            <span className="val">{pct(g.comments / Math.max(total, 1), 1)} · {num(g.comments)}</span>
          </>
        );
        const label = `${g.label}: ${num(g.comments)} comments, ${pct(g.comments / Math.max(total, 1), 1)} of comments in view${g.need !== "noise" ? `, name agreement ${pct(agree, 0)}` : ""}${g.uncertain ? ", uncertain" : ""}`;
        if (onSelect && top && g.need !== "noise") {
          return <button key={g.need} type="button" role="listitem" className={`need-row${g.uncertain ? " uncertain" : ""}`} onClick={() => onSelect(top.cluster_id)} aria-label={`${label}. Show cluster detail`}>{inner}</button>;
        }
        if (hrefFor && g.need !== "noise") {
          return <Link key={g.need} role="listitem" href={hrefFor(g)} className={`need-row${g.uncertain ? " uncertain" : ""}`} aria-label={`${label}. Open evidence`}>{inner}</Link>;
        }
        return <div key={g.need} role="listitem" className={`need-row${g.uncertain ? " uncertain" : ""}`} aria-label={label}>{inner}</div>;
      })}
    </div>
  );
}
