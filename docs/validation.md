# Validation

Validated locally on 2026-10-29 with Node 24 and Python 3.12.

- TypeScript checks and the Next production build pass. Lint retains one inherited hook-dependency warning in `draggable.tsx`; no new lint errors or warnings remain.
- 20 JavaScript tests pass: calibrated matrix results against OpenCV examples, measurement parsing, literal PDF text, immutable source files, stale generation handling, vector stitching, physical page extents, and blank pages.
- 17 Python tests pass: geometry, offsets, hems/folds, vector PDF export, calibration/crop/rotation/UserUnit, immutable originals, and explicit partial results.
- The supplied WBM pants PDF was opened in the production browser. Size M automatically hides the other size layers and retains shared marks. The detected defaults are 3/8-inch seams, 1-inch muslin allowance, and 2-inch hems. Eight pieces generate immediately; six require boundary review. Partial preparation was explicitly selected for this check.
- The resulting PDF rendered through the upstream projection viewer, including text, grainlines, control lines, original cutting lines, sewing lines, and muslin cutting lines. Mirroring twice restored exactly the previous projection transform.
- Input Mono and both PDF text/annotation styles were verified loaded in the browser.
- The installed macOS launcher executable cold-started both loopback servers. A second launch reused the same server PID. The app Info.plist and icon resources validate.
- A production dependency audit reports zero high or critical advisories after the lock refresh and scoped PostCSS/Zod patch overrides. Two moderate and one low transitive advisories remain; this is not a claim of a completely vulnerability-free dependency graph.

Physical projector/mat calibration was not performed. Align and measure the real projected calibration grid before cutting, as required by the upstream workflow. Do not infer physical output size from the browser's zoomed-out overview.
