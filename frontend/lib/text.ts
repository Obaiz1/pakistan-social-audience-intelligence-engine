/** Script detection for direction handling (pure; unit-tested). Urdu-script excerpts render rtl; Roman Urdu stays ltr. */

const ARABIC_BLOCK = /[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]/g;
const LATIN = /[A-Za-z]/g;

/** True when Arabic-script letters (Urdu) make up more than half of the letters in the text. */
export function isUrduScript(text: string | null | undefined): boolean {
  if (!text) return false;
  const ar = text.match(ARABIC_BLOCK)?.length ?? 0;
  const la = text.match(LATIN)?.length ?? 0;
  return ar > 0 && ar > la;
}

export function dirFor(text: string | null | undefined): "rtl" | "ltr" {
  return isUrduScript(text) ? "rtl" : "ltr";
}
