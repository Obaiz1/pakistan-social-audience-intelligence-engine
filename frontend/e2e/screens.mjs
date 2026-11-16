// Visual + accessibility QA: every route × {375, 1440} × {dark, light}.
// Usage: APP_URL=http://127.0.0.1:3000 [QA_TAG=local] node e2e/screens.mjs
// Saves screenshots to docs/screenshots/<tag>/ and a JSON report to docs/evidence/qa-screens-<tag>.json.
import { mkdirSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const BASE = (process.env.APP_URL || "http://127.0.0.1:3000").replace(/\/$/, "");
const TAG = process.env.QA_TAG || "local";
const ROUTES = ["/", "/content", "/audience", "/comments", "/anomalies", "/campaigns", "/recommendations", "/data", "/reports", "/methodology"];
const WIDTHS = [375, 1440];
const THEMES = ["dark", "light"];
const shots = new URL(`../../docs/screenshots/${TAG}/`, import.meta.url);
const evidence = new URL("../../docs/evidence/", import.meta.url);
mkdirSync(shots, { recursive: true });
mkdirSync(evidence, { recursive: true });

const browser = await chromium.launch();
const results = [];
for (const theme of THEMES) {
  for (const width of WIDTHS) {
    const ctx = await browser.newContext({ viewport: { width, height: 900 }, colorScheme: theme });
    await ctx.addInitScript((t) => { try { localStorage.setItem("audienceiq.theme", t); } catch { /* ignore */ } }, theme);
    const page = await ctx.newPage();
    for (const route of ROUTES) {
      const errors = [];
      const apiErrors = [];
      page.removeAllListeners("console");
      page.removeAllListeners("response");
      page.on("console", (m) => m.type() === "error" && errors.push(m.text().slice(0, 200)));
      page.on("response", (r) => r.url().includes("/api/v1/") && r.status() >= 500 && apiErrors.push(`${r.status()} ${r.url()}`));
      const res = await page.goto(`${BASE}${route}`, { waitUntil: "networkidle", timeout: 60000 }).catch((e) => ({ status: () => String(e) }));
      await page.waitForTimeout(400);
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
      const file = `${route === "/" ? "overview" : route.slice(1)}-${width}-${theme}.png`;
      await page.screenshot({ path: fileURLToPath(new URL(file, shots)), fullPage: width === 1440 && route === "/" });
      const status = typeof res?.status === "function" ? res.status() : null;
      const ok = status === 200 && !audit.overflow && audit.h1 >= 1 && !errors.length && !apiErrors.length && !audit.unnamed.length;
      results.push({ route, width, theme, status, ok, ...audit, consoleErrors: errors, apiErrors, screenshot: `docs/screenshots/${TAG}/${file}` });
      console.log(`${ok ? "OK  " : "FAIL"} ${theme} ${width}px ${route}${audit.overflow ? ` overflow(${audit.scrollWidth})` : ""}${errors.length ? ` console:${errors.length}` : ""}${audit.unnamed.length ? ` unnamed:${audit.unnamed.length}` : ""}`);
    }
    await ctx.close();
  }
}
await browser.close();
const summary = { base: BASE, tag: TAG, at: new Date().toISOString(), passed: results.filter((r) => r.ok).length, total: results.length, results };
writeFileSync(new URL(`qa-screens-${TAG}.json`, evidence), JSON.stringify(summary, null, 2));
console.log(`\n${summary.passed}/${summary.total} route × width × theme checks clean`);
process.exit(summary.passed === summary.total ? 0 : 1);
