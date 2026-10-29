import { spawnSync } from "node:child_process";
import { writeFileSync, mkdirSync } from "node:fs";
import { resolve } from "node:path";
const result = spawnSync(
  process.env.PATTERN_STUDIO_PYTHON || resolve(".venv/bin/python"),
  [
    "-c",
    "import json; from pattern_engine.api.main import app; print(json.dumps(app.openapi()))",
  ],
  {
    env: { ...process.env, PYTHONPATH: resolve("services/engine/src") },
    encoding: "utf8",
  },
);
if (result.status !== 0) throw new Error(result.stderr);
mkdirSync(".runtime", { recursive: true });
writeFileSync(".runtime/openapi.json", result.stdout);
const generate = spawnSync(
  process.execPath,
  [
    "node_modules/openapi-typescript/bin/cli.js",
    ".runtime/openapi.json",
    "-o",
    "app/_features/linework/api/schema.ts",
  ],
  { stdio: "inherit" },
);
process.exitCode = generate.status || 0;
