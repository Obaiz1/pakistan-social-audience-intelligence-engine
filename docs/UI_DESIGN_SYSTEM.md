# UI design system — "Editorial Intelligence"

AudienceIQ PK reads like a well-edited analytics brief: a serif headline states the question, a short lede states the answer's scope, and every figure underneath links to the evidence that produced it. This file documents the system as implemented in `frontend/app/globals.css`, `frontend/app/layout.tsx` and `frontend/components/`.

> The `frontend-design` plugin named in the brief is **not installed** in this environment (installing it requires the interactive `/plugin install` command). The design below follows the brief's written specification; the plugin was not run.

## Principles
1. **The five questions are the spine.** Navigation, the overview, the stepper and the printable brief all follow attention → needs → unusual → segments → action.
2. **Every number has a trail.** KPIs, need bars, evidence chips and segment cards are links to the screen that computed them.
3. **Uncertainty is visible, not footnoted.** Mixed/unclustered groups are striped, not hidden; cards show evidence strength, sample size and a caveat; anomaly drawers warn when the peer cohort is broad or small.
4. **The data mode is always on screen.** A banner, a badge in the top bar and a chip on every method note say *Synthetic demo*, *Observed* or *Imported*.
5. **No decoration without data.** No stock imagery, no gradients behind charts, no fake trend arrows.

## Typography
| Role | Font | Where |
|---|---|---|
| Headlines (`h1`, `.serif`, brand) | Newsreader Variable (`@fontsource-variable/newsreader` 5.3.0) | Page heads, hero, segment/action card titles |
| UI and body | Geist Sans (`geist` 1.9.0 via `next/font`) | Everything else |
| Identifiers, numbers in code | Geist Mono | Run IDs, post IDs, model versions |
| Urdu script | Noto Naskh Arabic 400/600 (`@fontsource/noto-naskh-arabic` 5.3.0) | `.urdu` spans, set by `<Bidi>` |

Numbers use `font-variant-numeric: tabular-nums` in tables and KPIs.

## Colour tokens
Defined on `:root`, redefined for `[data-theme="dark"]` and for `prefers-color-scheme: dark` when no theme is chosen. The theme is applied before paint by an inline script (`localStorage["audienceiq.theme"]`).

| Token | Light | Dark | Use |
|---|---|---|---|
| `--canvas` | `#f7f8f6` | `#10191d` | Page background |
| `--card` | `#ffffff` | `#182429` | Panels, cards |
| `--text` | `#152126` | `#e9f0ed` | Body text |
| `--text-3` | `#5f6a71` | `#93a19e` | Secondary text (≥ 4.5:1 on canvas) |
| `--accent` | `#087e73` | `#4fc1b0` | Fills, borders, focus, links |
| `--accent-text` | `#066b62` | `#6fd6c5` | Accent-coloured *text* on tinted backgrounds (added after the axe-core pass) |
| `--amber` / `--amber-fill` | `#8a5a0b` / `#d79c37` | `#e7b45a` | Synthetic mode, warnings |
| `--critical` | `#a8432c` | `#ef8f78` | Errors, "below cohort" flags |
| `--heat` | `8,126,115` | `28,120,110` | Heat-table cells (dark base deepened so light numerals keep ≥ 4.5:1) |
| `--c1…--c10`, `--p-*` | categorical | categorical | Chart series, platform colours |

## Layout
- **Shell:** left rail (collapsible, off-canvas below 900 px with an "Open navigation" button), sticky top bar (breadcrumbs, mode badge, freshness, dataset switcher, theme toggle), mode banner above everything.
- **Rail groups:** Start · The five questions (numbered 1–5) · Explore · Evidence & data.
- **Page head:** eyebrow (`Question N · Name` or `Evidence & data · Name`), serif `h1`, lede ≤ 70 ch.
- **Grids:** `.cols-2`, `.cols-3`, `.cols-4`, `.cols-5`, `.cols-7-5` (7:5 split); all collapse to one column below 900 px.
- **Filter bar:** sticky under the top bar (`top: 64px`); filters live in the URL so every view is shareable.
- **Print:** rail, top bar, banner, filter bar, toasts and `.no-print` are hidden; panels lose shadows; used by `/reports/brief`.

## Components (`frontend/components/`)
| Component | File | Notes |
|---|---|---|
| `Shell`, `DatasetSwitcher`, `ThemeToggle`, `Banner` | `shell.tsx` | Skip link is the first tab stop (`layout.tsx`) |
| `QuestionStepper` | `story.tsx` | `aria-current="step"`; short labels on mobile |
| `PageHead`, `Panel`, `Kpi` (`href` → link), `Notice`, `Empty`, `ErrorState`, `LoadingPage`, `Skeleton`, `Segmented`, `ChartTable`, `Drawer`, `Pager`, `MethodNote`, `ModeBadge`, `Bidi`, `TextCell` | `ui.tsx` | `ChartTable` gives every chart an accessible table twin |
| `NeedsDistribution` | `needs.tsx` | Uncertain groups (mixed/noise) striped |
| `ToastProvider` / `useToast` | `toast.tsx` | `aria-live`, auto-dismiss 4.5 s |
| Charts (`CIPlot`, `HBar`, `Histogram`, `Trend`, …) | `charts.tsx` | Recharts 3.10.1 |

## Bidirectional text
`lib/text.ts` decides direction by majority script: Urdu-script excerpts render `dir="rtl" lang="ur"` in Naskh; Roman Urdu, English and Latin-majority mixed text render `dir="ltr"` with `unicode-bidi: isolate`, so an Urdu word inside a Latin sentence stays in place. Unit-tested in `frontend/tests/text-status.test.ts`.

## Accessibility rules applied
- WCAG 2.1 AA checked with axe-core on every route at 390 and 1440 px in both themes (see `UI_QA_REPORT.md`).
- Scrollable tables are focusable regions (`tabIndex=0`) with a visible focus ring.
- Visible label text is part of every accessible name (KPI links use an `sr-only` suffix, not an overriding `aria-label`).
- Drawers trap focus and close on Escape; the stepper and segmented controls expose `aria-current` / `aria-pressed`.
- Workflow status selects carry an `sr-only` label naming the card.

## Workflow status (Action center)
`New → In review → Planned → Done`, stored per dataset in `localStorage["audienceiq.actions.<dataset_id>"]` (`lib/status.ts`). The public server is read-only, so the UI says "saved in this browser only". It is not shared between users.
