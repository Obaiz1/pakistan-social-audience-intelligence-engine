import { describe, expect, it } from "vitest";
import { dirFor, isUrduScript } from "../lib/text";
import { parseStatuses, storageKey, withStatus } from "../lib/status";

describe("isUrduScript / dirFor", () => {
  it("detects Urdu (Arabic-block) script", () => {
    expect(isUrduScript("قیمت کیا ہے؟")).toBe(true);
    expect(dirFor("قیمت کیا ہے؟")).toBe("rtl");
  });
  it("treats Roman Urdu and English as LTR", () => {
    expect(isUrduScript("price kya hai bhai")).toBe(false);
    expect(dirFor("Delivery kab tak hogi?")).toBe("ltr");
  });
  it("uses the majority script for mixed text", () => {
    expect(isUrduScript("قیمت price")).toBe(false);
    expect(isUrduScript("یہ بہت اچھا ہے ok")).toBe(true);
  });
  it("handles empty and null-ish input", () => {
    expect(isUrduScript("")).toBe(false);
    expect(dirFor("123 !!")).toBe("ltr");
  });
});

describe("workflow statuses", () => {
  it("namespaces storage by dataset", () => {
    expect(storageKey("synthetic-demo")).toBe("audienceiq.actions.synthetic-demo");
  });
  it("parses only known statuses and survives bad JSON", () => {
    expect(parseStatuses('{"a":"planned","b":"bogus","c":3}')).toEqual({ a: "planned" });
    expect(parseStatuses("not json")).toEqual({});
    expect(parseStatuses(null)).toEqual({});
  });
  it("drops the default status instead of storing it", () => {
    const m = withStatus({ a: "review" }, "b", "done");
    expect(m).toEqual({ a: "review", b: "done" });
    expect(withStatus(m, "a", "new")).toEqual({ b: "done" });
  });
});

import { HEAT_MAX_ALPHA, heatAlpha } from "../lib/format";

describe("heatAlpha", () => {
  it("scales with share and never exceeds the contrast-safe cap", () => {
    expect(heatAlpha(0)).toBe(0);
    expect(heatAlpha(null)).toBe(0);
    expect(heatAlpha(0.1)).toBeCloseTo(0.22);
    expect(heatAlpha(0.9)).toBe(HEAT_MAX_ALPHA);
  });
});
