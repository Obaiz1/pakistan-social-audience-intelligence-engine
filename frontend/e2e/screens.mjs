// Visual + accessibility QA.
//  A) every route × {390, 1440} × {dark, light}: status, overflow, h1, unnamed controls, console/API errors, axe-core (WCAG 2.1 A/AA).
//  B) key screens × {320, 375, 768, 1280} (light): overflow + screenshot.
// Usage: APP_URL=http://127.0.0.1:3000 [QA_TAG=local] [QA_DATASET=<id>] node e2e/screens.mjs
// Saves screenshots to docs/screenshots/<tag>/ and a JSON report to docs/evidence/qa-screens-<tag>.json.
import { mkdirSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import AxeBuilder from "@axe-core/playwright";
import { chromium } from "playwright";

const BASE = (process.env.APP_URL || "http://127.0.0.1:3000").replace(/\/$/, "");
const TAG = process.env.QA_TAG || "local";
const ROUTES = ["/", "/content", "/audience", "/segments", "/comments", "/anomalies", "/campaigns", "/recommendations", "/data", "/model", "/reports", "/reports/brief", "/methodology"];
const KEY_ROUTES = ["/", "/audience", "/segments", "/recommendations"];
const shots = new URL(`../../docs/screenshots/${TAG}/`, import.meta.url);
const evidence = new URL("../../docs/evidence/", import.meta.url);
mkdirSync(shots, { recursive: true });
mkdirSync(evidence, { recursive: true });
const slug = (r) => (r === "/" ? "overview" : r.slice(1).replace(/\//g, "-"));

const browser = await chromium.launch();
const results = [];

async function check(ctx, route, width, theme, { axe, fullPage }) {
  const page = await ctx.newPage();
  const errors = [];
  const apiErrors = [];
  page.on("console", (m) => m.type() === "error" && errors.push(m.text().slice(0, 200)));
  page.on("pageerror", (e) => errors.push(`pageerror: ${String(e).slice(0, 200)}`));
  page.on("response", (r) => r.url().includes("/api/v1/") && r.status() >= 500 && apiErrors.push(`${r.status()} ${r.url()}`));
  const res = await page.goto(`${BASE}${route}`, { waitUntil: "networkidle", timeout: 90000 }).catch((e) => ({ status: () => String(e) }));
  await page.waitForTimeout(500);
  const audit = await page.evaluate(() => {
    const unnamed = [...document.querySelectorAll("button, a[href], select, input")].filter((el) => {
      const name = el.getAttribute("aria-label") || el.textContent?.trim() || el.getAttribute("title") || (el.id && document.querySelector(`label[for="${el.id}"]`)?.textContent) || el.closest("label")?.textContent;
      return !name || !name.trim();
    }).map((el) => el.outerHTML.slice(0, 80));
    return {
      overflow: document.documentElement.scrollWidth > window.innerWidth + 1,
      scrollWidth: document.documentElement.scrollWidth,
      h1: document.querySelectorAll("h1").length,
      unnamed: unnamed.slice(0, 5),
      imgNoAlt: [...document.querySelectorAll("img")].filter((i) => !i.hasAttribute("alt")).length,
      theme: document.documentElement.dataset.theme || "system",
      banner: document.querySelector(".banner")?.textContent?.slice(0, 60) || null,
    };
  });
  let axeResult = null;
  if (axe) {
    const r = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
    const v = r.violations.map((x) => ({ id: x.id, impact: x.impact, nodes: x.nodes.length, sample: x.nodes.slice(0, 2).map((n) => n.target.join(" ")) }));
    axeResult = { serious: v.filter((x) => x.impact === "serious" || x.impact === "critical"), other: v.filter((x) => x.impact !== "serious" && x.impact !== "critical") };
  }
  const file = `${slug(route)}-${width}-${theme}.png`;
  await page.screenshot({ path: fileURLToPath(new URL(file, shots)), fullPage });
  const status = typeof res?.status === "function" ? res.status() : null;
  const ok = status === 200 && !audit.overflow && audit.h1 >= 1 && !errors.length && !apiErrors.length && !audit.unnamed.length && !(axeResult?.serious.length);
  results.push({ route, width, theme, status, ok, ...audit, axe: axeResult, consoleErrors: errors, apiErrors, screenshot: `docs/screenshots/${TAG}/${file}` });
  const ax = axeResult ? ` axe:${axeResult.serious.length}${axeResult.serious.length ? `(${axeResult.serious.map((x) => x.id).join(",")})` : ""}` : "";
  console.log(`${ok ? "OK  " : "FAIL"} ${theme} ${width}px ${route}${audit.overflow ? ` overflow(${audit.scrollWidth})` : ""}${errors.length ? ` console:${errors.length}` : ""}${audit.unnamed.length ? ` unnamed:${audit.unnamed.length}` : ""}${ax}`);
  await page.close();
}

async function context(width, theme) {
  const ctx = await browser.newContext({ viewport: { width, height: 900 }, colorScheme: theme });
  await ctx.addInitScript(([t, ds]) => {
    try {
      localStorage.setItem("audienceiq.theme", t);
      if (ds) localStorage.setItem("audienceiq.dataset", ds);
    } catch { /* ignore */ }
  }, [theme, process.env.QA_DATASET || ""]);
  return ctx;
}

for (const theme of ["light", "dark"]) {
  for (const width of [390, 1440]) {
    const ctx = await context(width, theme);
    for (const route of ROUTES) await check(ctx, route, width, theme, { axe: true, fullPage: width === 1440 && (route === "/" || route === "/reports/brief") });
    await ctx.close();
  }
}
for (const width of [320, 375, 768, 1280]) {
  const ctx = await context(width, "light");
  for (const route of KEY_ROUTES) await check(ctx, route, width, "light", { axe: false, fullPage: false });
  await ctx.close();
}
await browser.close();
const axeSerious = results.reduce((n, r) => n + (r.axe?.serious.length ?? 0), 0);
const summary = { base: BASE, tag: TAG, at: new Date().toISOString(), passed: results.filter((r) => r.ok).length, total: results.length, axe_serious_total: axeSerious, results };
writeFileSync(new URL(`qa-screens-${TAG}.json`, evidence), JSON.stringify(summary, null, 2));
console.log(`\n${summary.passed}/${summary.total} route × width × theme checks clean · axe serious/critical: ${axeSerious}`);
process.exit(summary.passed === summary.total ? 0 : 1);
