import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { resolve } from "node:path";

const python =
  process.env.PATTERN_STUDIO_PYTHON ||
  (existsSync(".venv/bin/python") ? resolve(".venv/bin/python") : "python3");
const children = [];
let stopping = false;
function stop(code = 0) {
  if (stopping) return;
  stopping = true;
  for (const child of children) child.kill("SIGTERM");
  process.exitCode = code;
}
function start(command, args, options = {}) {
  const child = spawn(command, args, { stdio: "inherit", ...options });
  children.push(child);
  child.on("error", (error) => {
    console.error(error.message);
    stop(1);
  });
  child.on("exit", (code) => stop(code || 0));
  return child;
}
start(
  python,
  [
    "-m",
    "uvicorn",
    "pattern_engine.api.main:app",
    "--host",
    "127.0.0.1",
    "--port",
    "8000",
  ],
  {
    cwd: resolve("services/engine"),
    env: {
      ...process.env,
      PYTHONPATH: resolve("services/engine/src"),
      PATTERN_STUDIO_DATA: resolve(".runtime"),
    },
  },
);
start(process.execPath, [
  resolve("node_modules/next/dist/bin/next"),
  process.env.PATTERN_PROJECTOR_PRODUCTION === "1" ? "start" : "dev",
  "--hostname",
  "127.0.0.1",
  "--port",
  "3000",
]);
process.on("SIGINT", () => stop());
process.on("SIGTERM", () => stop());
