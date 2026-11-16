import { describe, expect, it } from "vitest";
import { buildQuery, countActive, readFilters, withParam } from "@/lib/query";

describe("buildQuery", () => {
  it("drops empty values, keeps arrays and sorts keys", () => {
    expect(buildQuery({ b: "x", a: 1, c: null, d: "", platform: ["Instagram", "TikTok"] })).toBe(
      "?a=1&b=x&platform=Instagram&platform=TikTok",
    );
    expect(buildQuery({})).toBe("");
  });
  it("encodes Urdu and spaces", () => {
    expect(buildQuery({ q: "قیمت کیا" })).toBe("?q=%D9%82%DB%8C%D9%85%D8%AA+%DA%A9%DB%8C%D8%A7");
  });
});

describe("filters", () => {
  it("reads only known multi-valued filter keys", () => {
    const sp = new URLSearchParams("platform=Instagram&platform=TikTok&brand=Brand%20A&page=3&foo=bar");
    expect(readFilters(sp)).toEqual({ platform: ["Instagram", "TikTok"], brand: ["Brand A"] });
    expect(countActive(readFilters(sp))).toBe(2);
  });
  it("withParam replaces a key and resets pagination", () => {
    const next = withParam(new URLSearchParams("platform=Facebook&page=4"), "platform", "YouTube");
    expect(next.toString()).toBe("platform=YouTube");
    expect(withParam(next, "platform", null).toString()).toBe("");
  });
});
