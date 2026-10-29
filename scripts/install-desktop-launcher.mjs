import { execFileSync } from "node:child_process";
import { mkdirSync, writeFileSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { homedir } from "node:os";
const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const destination = resolve(
  process.argv[2] || resolve(homedir(), "Desktop", "Pattern Projector.app"),
);
if (
  existsSync(destination) &&
  !existsSync(resolve(destination, "Contents", "pattern-projector-launcher"))
) {
  throw new Error(`A different application already exists at ${destination}`);
}
const contents = resolve(destination, "Contents");
mkdirSync(resolve(contents, "MacOS"), { recursive: true });
mkdirSync(resolve(contents, "Resources"), { recursive: true });
writeFileSync(resolve(contents, "pattern-projector-launcher"), root);
writeFileSync(
  resolve(contents, "Info.plist"),
  `<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict><key>CFBundleName</key><string>Pattern Projector</string><key>CFBundleDisplayName</key><string>Pattern Projector</string><key>CFBundleIdentifier</key><string>com.vince.pattern-projector.local</string><key>CFBundleIconFile</key><string>PatternProjector.icns</string><key>CFBundleExecutable</key><string>PatternProjector</string><key>CFBundlePackageType</key><string>APPL</string><key>CFBundleVersion</key><string>1</string><key>LSUIElement</key><true/></dict></plist>`,
);
const quote = (value) => `'${value.replaceAll("'", "'\\''")}'`;
writeFileSync(
  resolve(contents, "MacOS", "PatternProjector"),
  `#!/bin/sh\nexec ${quote(process.execPath)} ${quote(resolve(root, "scripts/launch.mjs"))} "$@"\n`,
  { mode: 0o755 },
);
if (process.platform === "darwin") {
  const iconset = resolve(root, ".runtime", "desktop.iconset");
  mkdirSync(iconset, { recursive: true });
  for (const size of [16, 32, 128, 256, 512]) {
    for (const density of [1, 2]) {
      const file = resolve(
        iconset,
        `icon_${size}x${size}${density === 2 ? "@2x" : ""}.png`,
      );
      execFileSync(
        "/usr/bin/sips",
        [
          "-z",
          String(size * density),
          String(size * density),
          resolve(root, "public/512.png"),
          "--out",
          file,
        ],
        { stdio: "ignore" },
      );
    }
  }
  execFileSync("/usr/bin/iconutil", [
    "-c",
    "icns",
    iconset,
    "-o",
    resolve(contents, "Resources", "PatternProjector.icns"),
  ]);
}
console.log(`Installed ${destination}`);
