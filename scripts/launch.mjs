import { spawn, execFileSync } from "node:child_process";
import {
  existsSync,
  mkdirSync,
  openSync,
  writeFileSync,
  readFileSync,
  rmSync,
  statSync,
} from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
process.chdir(root);
const state = resolve(".runtime");
mkdirSync(state, { recursive: true });
const log = resolve(state, "launcher.log");
const pidFile = resolve(state, "launcher.pid");
const lock = resolve(state, "launch.lock");
const url = "http://127.0.0.1:3000/en/calibrate";
async function running() {
  try {
    return (
      await fetch("http://127.0.0.1:3000/api/linework/health", {
        signal: AbortSignal.timeout(2000),
      })
    ).ok;
  } catch {
    return false;
  }
}
if (process.argv.includes("--stop")) {
  if (existsSync(pidFile)) {
    const pid = Number(readFileSync(pidFile, "utf8"));
    try {
      const command = execFileSync(
        "/bin/ps",
        ["-p", String(pid), "-o", "command="],
        { encoding: "utf8" },
      );
      if (command.includes(resolve("scripts/dev.mjs")))
        process.kill(pid, "SIGTERM");
    } catch {
      /* Already stopped. */
    }
    rmSync(pidFile, { force: true });
  }
  process.exit(0);
}
let ownsLock = false;
try {
  if (!(await running())) {
    if (existsSync(lock) && Date.now() - statSync(lock).mtimeMs > 180000)
      rmSync(lock, { recursive: true, force: true });
    try {
      mkdirSync(lock);
      ownsLock = true;
    } catch {
      /* Another click is already launching. */
    }
    if (ownsLock) {
      const fd = openSync(log, "a");
      const child = spawn(process.execPath, [resolve("scripts/dev.mjs")], {
        cwd: root,
        env: {
          ...process.env,
          PATH: `${dirname(process.execPath)}:/opt/homebrew/bin:/usr/bin:/bin`,
          PATTERN_PROJECTOR_PRODUCTION: existsSync(".next/BUILD_ID")
            ? "1"
            : "0",
        },
        detached: true,
        stdio: ["ignore", fd, fd],
      });
      child.unref();
      writeFileSync(pidFile, String(child.pid));
    }
    let ready = false;
    for (let i = 0; i < 90; i++) {
      if (await running()) {
        ready = true;
        break;
      }
      await new Promise((resolve) => setTimeout(resolve, 1000));
    }
    if (!ready) throw new Error(`Pattern Projector did not start. See ${log}`);
  }
  if (!process.argv.includes("--no-open"))
    spawn("/usr/bin/open", [url], { detached: true, stdio: "ignore" }).unref();
  console.log(url);
} catch (error) {
  writeFileSync(log, `\n${error.stack || error}\n`, { flag: "a" });
  if (!process.argv.includes("--no-open"))
    spawn("/usr/bin/open", [log], { detached: true, stdio: "ignore" }).unref();
  process.exitCode = 1;
} finally {
  if (ownsLock) rmSync(lock, { recursive: true, force: true });
}
