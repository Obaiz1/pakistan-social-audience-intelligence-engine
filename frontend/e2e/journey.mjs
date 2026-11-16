// Five-question browser journey (Q1–Q5) + data/report/method pages.
// Usage: APP_URL=http://127.0.0.1:3000 [QA_TAG=local] node e2e/journey.mjs
// Writes docs/evidence/e2e-journey-<tag>.json and exits non-zero on any failed step.
import { mkdirSync, writeFileSync } from "node:fs";
import { chromium } from "playwright";

const BASE = (process.env.APP_URL || "http://127.0.0.1:3000").replace(/\/$/, "");
const TAG = process.env.QA_TAG || "local";
const OUT = new URL("../../docs/evidence/", import.meta.url);

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
const consoleErrors = [];
const badResponses = [];
page.on("console", (m) => m.type() === "error" && consoleErrors.push(m.text().slice(0, 300)));
page.on("pageerror", (e) => consoleErrors.push(`pageerror: ${String(e).slice(0, 300)}`));
page.on("response", (r) => {
  if (r.url().includes("/api/v1/") && r.status() >= 400) badResponses.push(`${r.status()} ${r.url().replace(BASE, "")}`);
});

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
const visible = (sel) => page.locator(sel).first().waitFor({ state: "visible", timeout: 30000 });

await step("Overview loads with dataset banner and journey", async () => {
  await page.goto(`${BASE}/`, { waitUntil: "domcontentloaded" });
  await visible(".banner");
  await visible("nav.journey");
  const banner = await page.locator(".banner").first().innerText();
  await visible(".kpi");
  return banner.slice(0, 90);
});
await step("Q1 content comparison renders with CI table parity", async () => {
  await page.goto(`${BASE}/content`);
  await page.getByRole("heading", { name: "Which content attracts attention?" }).waitFor();
  await page.getByRole("button", { name: "Table" }).first().click();
  await visible("table.data");
  const rows = await page.locator("table.data").first().locator("tbody tr").count();
  if (rows < 3) throw new Error(`only ${rows} content-type rows`);
  await page.locator("button.link.mono").first().click();
  await visible(".drawer");
  await page.keyboard.press("Escape");
  return `${rows} content types; post drawer opened and closed with Escape`;
});
await step("Q1 filter by platform updates the URL", async () => {
  await page.selectOption("#f-platform", "Instagram");
  await page.waitForURL(/platform=Instagram/);
  return page.url().replace(BASE, "");
});
await step("Q2/Q4 audience clusters + cluster drill-down", async () => {
  await page.goto(`${BASE}/audience`);
  await visible(".cluster-card");
  const n = await page.locator(".cluster-card").count();
  await page.locator(".cluster-card").first().click();
  await visible("#cluster-detail");
  const title = await page.locator("#cluster-detail h2").first().innerText();
  if (!(await page.getByText("Why this group exists").isVisible())) throw new Error("no explanation section");
  return `${n} clusters; opened "${title}"`;
});
await step("Q2 comment explorer filters by language", async () => {
  await page.goto(`${BASE}/comments`);
  await visible("table.data");
  await page.selectOption("#c-language", "urdu");
  await page.waitForURL(/language=urdu/);
  await visible("table.data tbody tr");
  return `${await page.locator("table.data tbody tr").count()} Urdu rows on page 1`;
});
await step("Q3 anomalies list + detail with baseline", async () => {
  await page.goto(`${BASE}/anomalies`);
  await visible("table.data");
  await page.locator("table.data button.link").first().click();
  await visible(".drawer .kv");
  const text = await page.locator(".drawer").innerText();
  if (!/cohort median/i.test(text)) throw new Error("no baseline shown");
  if (!/not evidence of fraud/i.test(text)) throw new Error("caveat missing");
  return text.split("\n").find((l) => /cohort median/i.test(l))?.slice(0, 140);
});
await step("Q1/Q4 campaigns with needs-by-campaign table", async () => {
  await page.goto(`${BASE}/campaigns`);
  await page.getByRole("heading", { name: /Audience needs by campaign/ }).waitFor();
  return `${await page.locator("table.data").count()} tables`;
});
await step("Q5 recommendations with linked evidence", async () => {
  await page.goto(`${BASE}/recommendations`);
  await visible("article.rec");
  const cards = await page.locator("article.rec").count();
  const evidence = await page.locator("article.rec a.chip").count();
  if (!evidence) throw new Error("no evidence links");
  await page.locator("article.rec a.chip").first().click();
  // match the pathname only (the production hostname "audienceiq-pk" would otherwise satisfy /audience/)
  await page.waitForURL((u) => /^\/(audience|anomalies|campaigns|content)/.test(new URL(u).pathname));
  return `${cards} cards, ${evidence} evidence links; followed one to ${page.url().replace(BASE, "")}`;
});
await step("Data page: quality audit + import preview (validation only)", async () => {
  await page.goto(`${BASE}/data`);
  await page.getByText("Quality audit").first().waitFor();
  const posts = "post_id,brand,platform,likes,comments_count,published_at\n" + Array.from({ length: 25 }, (_, i) => `P${i},Brand Z,tiktok,${10 + i},${i},2026-09-0${1 + (i % 9)}T10:00:00Z`).join("\n");
  await page.locator('input[type="file"]').first().setInputFiles({ name: "posts.csv", mimeType: "text/csv", buffer: Buffer.from(posts) });
  await page.getByRole("button", { name: /Preview/ }).click();
  await page.getByText("Validation report").waitFor({ timeout: 30000 });
  return "preview + validation rendered";
});
await step("Reports offer CSV/Excel/PDF downloads", async () => {
  await page.goto(`${BASE}/reports`);
  const links = await page.locator('a[href*="/reports/export"]').count();
  const res = await page.request.get(`${BASE}/api/v1/reports/export?format=pdf`);
  if (res.status() !== 200) throw new Error(`pdf export ${res.status()}`);
  return `${links} export links; PDF ${res.headers()["content-type"]}`;
});
await step("Methodology shows the official Project 3 title", async () => {
  await page.goto(`${BASE}/methodology`);
  await page.getByRole("heading", { name: /Project 3: Pakistan Social Audience & Campaign Intelligence Engine/ }).waitFor();
  return "title visible";
});
await step("Health endpoint", async () => {
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
process.exit(result.passed === result.total && !unexpected.length ? 0 : 1);
