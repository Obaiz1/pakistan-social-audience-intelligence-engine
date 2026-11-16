"use client";

import Link from "next/link";

/** The five assignment questions as one story: attention → needs → unusual → segments → action. */
export const QUESTIONS = [
  { q: 1, href: "/content", title: "Attention", sub: "Which content attracts attention?" },
  { q: 2, href: "/audience", title: "Needs", sub: "What does the audience want?" },
  { q: 3, href: "/anomalies", title: "Unusual", sub: "Which patterns are unusual?" },
  { q: 4, href: "/segments", title: "Segments", sub: "Which needs to address?" },
  { q: 5, href: "/recommendations", title: "Actions", sub: "What should we do next?" },
] as const;

export function QuestionStepper({ current }: { current?: 1 | 2 | 3 | 4 | 5 }) {
  return (
    <nav className="qstep" aria-label="The five assignment questions">
      {QUESTIONS.map((s) => (
        <Link key={s.q} href={s.href} aria-current={current === s.q ? "step" : undefined} title={`Q${s.q} · ${s.sub}`}>
          <span className="n" aria-hidden="true">{s.q}</span>
          <span className="t">Q{s.q} · {s.title}</span>
          <span className="s">{s.sub}</span>
          <span className="m" aria-hidden="true">{s.title}</span>
          <span className="sr-only">{`Question ${s.q}: ${s.sub}`}</span>
        </Link>
      ))}
    </nav>
  );
}
