# Pattern Projector — Sewing & Muslin Fork

A local fork of [Pattern Projector](https://github.com/Pattern-Projector/pattern-projector), with a Python geometry engine for size-specific sewing lines and extra muslin cutting allowance. Upstream calibration, perspective correction, movement, rotation, mirroring, measuring, layer selection, and page stitching remain the projection foundation.

The original Pattern Studio implementation is preserved separately. Its PDF and geometry engine now lives in `services/engine`; the new React feature lives in `app/_features/linework`. The upstream MIT license and copyright are retained.

## Open on this Mac

Double-click **Pattern Projector.app** on the Desktop. It starts the web app and local geometry engine and opens **http://127.0.0.1:3000/en/calibrate**. Clicking again reuses the running app. No terminal is needed for normal use. The installed launcher points to this checkout, so keep this folder in place or reinstall the launcher after moving it.

To reinstall the desktop icon:

```sh
node scripts/install-desktop-launcher.mjs
```

To stop servers started by that launcher:

```sh
node scripts/launch.mjs --stop
```

Startup logs are in `.runtime/launcher.log`. The launcher uses a production build when available and development mode otherwise. The Python interpreter must be available in `.venv` or `PATTERN_STUDIO_PYTHON`.

## Sewing and muslin workflow

1. Calibrate the projector using the original Pattern Projector controls, then choose **Project** and open the PDF.
2. Open **SEWING / MUSLIN** on the right. Select a size. Non-size notches, grainlines, text, and control lines remain present.
3. Set the original seam allowance and the desired muslin allowance. Source suggestions are used when detected. Inputs accept decimals, fractions (`3/8`), and mixed fractions (`1 1/2`).
4. A `3/8″` original allowance and `1″` muslin allowance place the sewing line `3/8″` inward and the muslin cut `5/8″` outside the original cut along ordinary seams. Hems and confirmed fold edges have separate rules.
5. Review open boundaries and inferred fold/closing edges. Confirm only edges you have checked against the source, or explicitly accept a partial result. Unconfirmed pieces retain their original markings but receive no generated lines.
6. Click **GENERATE + PROJECT**. A derived vector PDF replaces the display inside the original projection pipeline. The source file is never overwritten. Use **Restore original** to return to native layers, or **Download PDF** to save the prepared version.

The review page arrows appear only for multi-page PDFs. Generation/export processes **all pages**, rather than silently exporting just the review page. The engine refuses incomplete results unless partial generation was explicitly enabled.

PDF reference-square measurements and optional PDF correction are separate from projector/mat calibration. Corrections apply before offsets, so requested allowances stay in physical units. Keep the upstream Pattern Scale at `1.00` when using generated linework; changing it restores the original view rather than stretching generated allowances. Actual physical projection still needs to be measured on your cutting surface.

## Local setup on another Mac

Use Node.js 20.19+ (Node 22 or 24 works) and Python 3.12 with Clipper2 wheels.

```sh
CYPRESS_INSTALL_BINARY=0 node .yarn/releases/yarn-1.22.21.cjs install
python3.12 -m venv .venv
.venv/bin/python -m pip install -e 'services/engine[test]'
node scripts/dev.mjs
```

The web app binds to loopback port `3000`, and the engine to loopback port `8000`. PDFs go only to that local engine. Files and workspace data in `.runtime/` are ignored by Git. Input Mono is loaded from the installed local font; no font binaries are redistributed. Upstream Google Analytics has been removed from this local fork.

## Development

```sh
yarn check
yarn test:unit --runInBand --coverage=false
yarn test:engine
yarn build
yarn generate:api
```

`generate:api` derives TypeScript types from the engine's OpenAPI schema. Keep the frontend contract generated rather than copying model definitions by hand. The build does not run a repository-wide formatter.

- [Fork architecture and upstream maintenance](docs/fork-architecture.md)
- [Geometry accuracy and limitations](docs/linework-accuracy.md)
- [Original upstream README](docs/upstream-readme.md)
- [Original upstream contribution guide](CONTRIBUTING.md)

The upstream maintainer has announced a separate rewrite; this public branch is in maintenance mode. This fork intentionally keeps its linework feature isolated so it can be ported if the rewrite becomes available. No feature PR is being submitted to upstream while its feature contributions are paused.
