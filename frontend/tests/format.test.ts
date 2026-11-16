import { describe, expect, it } from "vitest";
import { compact, label, metricValue, NA, num, pct, pval, ratio, NEED_LABEL } from "@/lib/format";

describe("missing values are never shown as zero", () => {
  it("renders null/undefined/NaN as N/A", () => {
    for (const fn of [num, pct, ratio, compact, pval]) {
      expect(fn(null)).toBe(NA);
      expect(fn(undefined)).toBe(NA);
      expect(fn(Number.NaN)).toBe(NA);
    }
  });
  it("but a real zero stays zero", () => {
    expect(num(0)).toBe("0");
    expect(pct(0)).toBe("0.0%");
  });
});

describe("formatting", () => {
  it("formats percentages, ratios, compact numbers and p-values", () => {
    expect(pct(0.1234)).toBe("12.3%");
    expect(ratio(1.234)).toBe("1.23");
    expect(compact(1530)).toBe("1.5K");
    expect(compact(2_400_000)).toBe("2.4M");
    expect(pval(0.0004)).toBe("< 0.001");
    expect(pval(0.0213)).toBe("0.021");
  });
  it("chooses units per metric", () => {
    expect(metricValue("er_views", 0.0512)).toBe("5.12%");
    expect(metricValue("share:order_issue", 0.62)).toBe("62%");
  });
  it("labels needs and falls back gracefully", () => {
    expect(label(NEED_LABEL, "size_fit")).toBe("Size & fit");
    expect(label(NEED_LABEL, "brand_new_need")).toBe("brand new need");
    expect(label(NEED_LABEL, null)).toBe(NA);
  });
});
