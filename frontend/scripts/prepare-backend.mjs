import { cpSync, mkdirSync, rmSync } from "node:fs";
import { fileURLToPath } from "node:url";

// Hosted builds: copy the Python package and the committed (read-only) dataset bundles beside the Vercel function.
// The copy is generated, git-ignored and never edited by hand (pattern from Repo B signalspend-ai).
const generated = fileURLToPath(new URL("../.backend/", import.meta.url));
const skip = (source) => !source.includes("__pycache__") && !source.endsWith(".pyc") && !source.includes(".pytest_cache");
rmSync(generated, { recursive: true, force: true });
mkdirSync(generated, { recursive: true });
cpSync(new URL("../../backend/audienceiq/", import.meta.url), `${generated}/audienceiq`, { recursive: true, filter: skip });
cpSync(new URL("../../data/datasets/", import.meta.url), `${generated}/data/datasets`, { recursive: true, filter: skip });
console.log("prepare-backend: copied audienceiq + data/datasets into .backend/");
