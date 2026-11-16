// Ten user journeys across the five-question story, evidence screens, exports, mobile and keyboard use.
// Usage: APP_URL=http://127.0.0.1:3000 [QA_TAG=local] node e2e/journey.mjs
// Writes docs/evidence/e2e-journey-<tag>.json and exits non-zero on any failed step.
import { mkdirSync, writeFileSync } from "node:fs";
import { chromium } from "playwright";

const BASE = (process.env.APP_URL || "http://127.0.0.1:3000").replace(/\/$/, "");
const TAG = process.env.QA_TAG || "local";
const OUT = new URL("../../docs/evidence/", import.meta.url);

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1440, height: 1000 }, acceptDownloads: true });
const page = await ctx.newPage();
const consoleErrors = [];
const badResponses = [];
const watch = (p) => {
  p.on("console", (m) => m.type() === "error" && consoleErrors.push(m.text().slice(0, 300)));
  p.on("pageerror", (e) => consoleErrors.push(`pageerror: ${String(e).slice(0, 300)}`));
  p.on("response", (r) => {
    if (r.url().includes("/api/v1/") && r.status() >= 400) badResponses.push(`${r.status()} ${r.url().replace(BASE, "")}`);
  });
};
watch(page);

const steps = [];
async function step(name, fn) {
  const t = Date.now();
  try {
    const detail = await fn();
    steps.push({ name, ok: true, ms: Date.now() - t, detail: detail ?? null });
    console.log(`PASS ${name}${detail ? ` — ${detail}` : ""}`);
  } catch (e) {
    steps.push({ name, ok: false, ms: Date.now() - t, error: String(e).slice(0, 400) });
    console.log(`FAIL ${name}: ${String(e).slice(0, 200)}`);
  }
}
const visible = (sel, p = page) => p.locator(sel).first().waitFor({ state: "visible", timeout: 30000 });
const path = (p = page) => new URL(p.url()).pathname;

await step("J1 Overview: mode banner, five answers, KPI drill-through", async () => {
  await page.goto(`${BASE}/`, { waitUntil: "domcontentloaded" });
  await visible(".banner");
  await visible("nav.journey .answer");
  const answers = await page.locator("nav.journey a").count();
  if (answers !== 5) throw new Error(`expected 5 question cards, got ${answers}`);
  await visible("a.kpi");
  await page.locator("a.kpi").first().click();
  await page.waitForURL((u) => new URL(u).pathname !== "/");
  return `5 answers; first KPI opened ${path()}`;
});

await step("J2 Q1 Attention: CI table, post drawer, platform filter, filtered CSV with metadata", async () => {
  await page.goto(`${BASE}/content`);
  await page.getByRole("heading", { name: "Which content attracts attention?" }).waitFor();
  await page.getByRole("button", { name: "Table" }).first().click();
  const rows = await page.locator("table.data").first().locator("tbody tr").count();
  if (rows < 3) throw new Error(`only ${rows} content-type rows`);
  await page.locator("button.link.mono").first().click();
  await visible(".drawer");
  await page.keyboard.press("Escape");
  await page.locator(".drawer").waitFor({ state: "hidden" });
  await page.selectOption("#f-platform", "Instagram");
  await page.waitForURL(/platform=Instagram/);
  const href = await page.getByRole("link", { name: /Filtered CSV/ }).getAttribute("href");
  if (!href?.includes("platform=Instagram")) throw new Error(`CSV link ignores filter: ${href}`);
  const csv = await (await page.request.get(new URL(href, BASE).toString())).text();
  const head = csv.split("\n").slice(0, 14).join("\n");
  for (const k of ["# disclaimer:", "# mode:", "# clustering run:", "# filters: platform="]) if (!head.includes(k)) throw new Error(`CSV header missing ${k}`);
  return `${rows} content types; drawer closed with Escape; CSV header carries disclaimer, mode, run and filters`;
});

await step("J3 Q2 Needs: price cluster → Roman-Urdu gloss → linked post → recommended action", async () => {
  await page.goto(`${BASE}/audience`);
  await visible(".cluster-card");
  await page.locator(".cluster-card", { hasText: /price/i }).first().click();
  await visible("#cluster-detail");
  const title = (await page.locator("#cluster-detail h2").first().innerText()).trim();
  await page.locator("#trail-comments select").selectOption("roman_urdu");
  await page.waitForURL(/clang=roman_urdu/);
  await visible("#trail-comments .gloss");
  const gloss = (await page.locator("#trail-comments .gloss").first().innerText()).slice(0, 80);
  await page.locator("#trail-posts button.link").first().click();
  await visible(".drawer");
  await page.keyboard.press("Escape");
  const action = page.locator("#trail-actions a").first();
  if (await action.count()) {
    await action.click();
    await page.waitForURL((u) => new URL(u).pathname === "/recommendations");
    return `"${title}" · ${gloss} · linked post opened · action ${new URL(page.url()).hash}`;
  }
  return `"${title}" · ${gloss} · linked post opened · no action passed the gates (shown as such)`;
});

await step("J4 Q3 Anomaly lab: ranked flags, baseline, cohort and caveat", async () => {
  await page.goto(`${BASE}/anomalies`);
  await page.getByText("Strongest flags (ranked)").first().waitFor();
  await page.locator("table.data button.link").first().click();
  await visible(".drawer .kv");
  const text = await page.locator(".drawer").innerText();
  if (!/cohort median/i.test(text)) throw new Error("no baseline shown");
  if (!/not evidence of fraud/i.test(text)) throw new Error("caveat missing");
  for (let i = 0; i < 30; i++) await page.keyboard.press(i % 7 === 6 ? "Shift+Tab" : "Tab");
  if (!(await page.evaluate(() => !!document.activeElement?.closest(".drawer")))) throw new Error("focus escaped the modal drawer");
  await page.keyboard.press("Escape");
  await page.locator(".drawer").waitFor({ state: "hidden" });
  return `${text.split("\n").find((l) => /cohort median/i.test(l))?.slice(0, 100)} · focus trapped in drawer`;
});

await step("J5 Q4 Segments: comment-level unit, cards, compare by brand", async () => {
  await page.goto(`${BASE}/segments`);
  await page.getByRole("heading", { name: /Which audience needs should the brand address/ }).waitFor();
  await page.getByText("Unit of analysis: comments").first().waitFor();
  await visible("article.rec");
  const cards = await page.locator("article.rec").count();
  await page.getByRole("group", { name: "Compare by" }).getByRole("button", { name: "Brand" }).click();
  await page.waitForURL(/compare_by=brand/);
  await visible("td.heat-cell");
  return `${cards} segments; compare table by brand rendered`;
});

await step("J6 Q5 Action center: evidence link + workflow status persists", async () => {
  await page.goto(`${BASE}/recommendations`);
  await visible("article.rec dl.opp");
  const first = page.locator("article.rec").first();
  for (const t of ["Opportunity", "Why it matters", "Evidence", "Suggested test", "Uncertainty"]) await first.locator("dt", { hasText: t }).waitFor();
  await first.locator("select").selectOption("planned");
  await page.locator(".toast").first().waitFor();
  await page.reload();
  await visible("article.rec select");
  const v = await page.locator("article.rec select").first().inputValue();
  if (v !== "planned") throw new Error(`status not persisted (got ${v})`);
  await page.locator("article.rec select").first().selectOption("new");
  const evidence = await page.locator("article.rec a.chip").count();
  if (!evidence) throw new Error("no evidence links");
  await page.locator("article.rec a.chip").first().click();
  await page.waitForURL((u) => /^\/(audience|anomalies|campaigns|content|segments)/.test(new URL(u).pathname));
  return `status saved across reload; ${evidence} evidence links; followed one to ${path()}`;
});

await step("J7 Model lab: audit metric definition, candidates, error cases", async () => {
  await page.goto(`${BASE}/model`);
  await page.getByRole("heading", { name: /How the audience clusters were made/ }).waitFor();
  const body = await page.locator("main").innerText();
  if (!/18\s?%/.test(body)) throw new Error("audit baseline (18 %) not stated");
  if (!/46\s?%/.test(body) || !/not the shipped figure/i.test(body)) throw new Error("exploratory 46 % not disambiguated");
  const rows = await page.locator("table.data tbody tr").count();
  return `audit metric defined; ${rows} table rows across candidates/errors/methods`;
});

await step("J8 Data hub: source status without a key, import preview validates only", async () => {
  await page.goto(`${BASE}/data`);
  await page.getByText("Source status").first().waitFor();
  // textContent, not innerText: badges are text-transformed to uppercase
  const panel = await page.locator(".panel", { hasText: "Source status" }).first().evaluate((el) => el.textContent ?? "");
  if (/AIza[0-9A-Za-z_-]{10,}/.test(panel)) throw new Error("something that looks like an API key is on the page");
  if (!/YouTube/.test(panel) || !/CSV import only/.test(panel)) throw new Error("platform support matrix missing");
  const posts = "post_id,brand,platform,likes,comments_count,published_at\n" + Array.from({ length: 25 }, (_, i) => `P${i},Brand Z,tiktok,${10 + i},${i},2026-09-0${1 + (i % 9)}T10:00:00Z`).join("\n");
  await page.locator('input[type="file"]').first().setInputFiles({ name: "posts.csv", mimeType: "text/csv", buffer: Buffer.from(posts) });
  await page.getByRole("button", { name: /Preview/ }).click();
  await page.getByText("Validation report").waitFor({ timeout: 30000 });
  return `${/not configured/.test(panel) ? "collector not configured (no key)" : "collector configured locally"}; preview + validation rendered`;
});

await step("J9 Reports → printable brief with the five answers and limitations", async () => {
  await page.goto(`${BASE}/reports`);
  await visible('a[href*="/reports/export"]');
  const links = await page.locator('a[href*="/reports/export"]').count();
  await page.getByRole("link", { name: /Open printable brief/ }).click();
  await page.waitForURL((u) => new URL(u).pathname === "/reports/brief");
  await page.getByRole("heading", { name: /Q1 · Which content attracts attention/ }).waitFor();
  for (const h of [/Q2 ·/, /Q3 ·/, /Q4 & Q5/, /Limitations/]) await page.getByRole("heading", { name: h }).waitFor();
  await page.emulateMedia({ media: "print" });
  const railHidden = await page.locator("nav.rail").evaluate((el) => getComputedStyle(el).display === "none");
  await page.emulateMedia({ media: "screen" });
  if (!railHidden) throw new Error("navigation still visible in print layout");
  const res = await page.request.get(`${BASE}/api/v1/reports/export?format=pdf`);
  if (res.status() !== 200) throw new Error(`pdf export ${res.status()}`);
  return `${links} export links; brief has Q1–Q5 + limitations; print hides navigation; PDF ${res.headers()["content-type"]}`;
});

await step("J10 Mobile (390px) navigation + keyboard, Urdu RTL and theme", async () => {
  const m = await browser.newPage({ viewport: { width: 390, height: 844 } });
  watch(m);
  await m.goto(`${BASE}/segments`);
  await visible("article.rec", m);
  const overflow = await m.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
  if (overflow) throw new Error("horizontal scroll at 390px");
  await m.getByRole("button", { name: "Open navigation" }).click();
  await m.getByRole("link", { name: /Action center/ }).click();
  await m.waitForURL((u) => new URL(u).pathname === "/recommendations");
  await m.close();

  await page.goto(`${BASE}/comments?language=urdu`);
  await visible("table.data tbody tr");
  const rtl = await page.locator('table.data [dir="rtl"][lang="ur"]').count();
  await page.keyboard.press("Tab");
  const skip = await page.evaluate(() => document.activeElement?.textContent?.trim());
  if (skip !== "Skip to content") throw new Error(`first Tab focused "${skip}"`);
  await page.keyboard.press("Enter");
  await page.selectOption("#c-sort", "-published_at");
  await page.waitForURL(/sort=-published_at/);
  const before = await page.evaluate(() => document.documentElement.dataset.theme || "system");
  await page.getByRole("button", { name: /Switch to (dark|light) theme/ }).click();
  const after = await page.evaluate(() => document.documentElement.dataset.theme);
  if (!after || after === before) throw new Error("theme did not toggle");
  await page.getByRole("button", { name: /Switch to (dark|light) theme/ }).click();
  return `no overflow at 390px; mobile menu navigates; skip link first in tab order; ${rtl} Urdu cells rtl; sort + theme toggle work`;
});

await step("API health", async () => {
  const r = await page.request.get(`${BASE}/api/v1/health`);
  const j = await r.json();
  if (j.status !== "ok") throw new Error(JSON.stringify(j));
  return `${j.app} v${j.version} · ${j.environment} · writes_enabled=${j.writes_enabled} · commit ${j.build_commit ?? "n/a"}`;
});

await browser.close();
const unexpected = badResponses.filter((r) => !r.startsWith("403 /api/v1/imports/confirm"));
const result = { base: BASE, tag: TAG, at: new Date().toISOString(), passed: steps.filter((s) => s.ok).length, total: steps.length,
  steps, consoleErrors, apiErrors: unexpected };
mkdirSync(OUT, { recursive: true });
writeFileSync(new URL(`e2e-journey-${TAG}.json`, OUT), JSON.stringify(result, null, 2));
console.log(`\n${result.passed}/${result.total} steps passed · console errors: ${consoleErrors.length} · API errors: ${unexpected.length}`);
process.exit(result.passed === result.total && !unexpected.length && !consoleErrors.length ? 0 : 1);
