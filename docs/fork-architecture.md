# Fork architecture

This checkout keeps Pattern Projector's Git history. The initial upstream base is `29af9debd5c38b9cf154e46db8b4e9e59a18922c`. `upstream` points to Pattern-Projector/pattern-projector and `origin` points to the user's fork. New code is on `codex/sewing-muslin-lines`; the original upstream license remains unchanged.

## Boundaries

- `app/[locale]/calibrate/page.tsx` remains the upstream composition layer. It owns calibration and native projection state and selects an immutable source file or a prepared derivative.
- `app/_features/linework/api` contains the local API client and generated OpenAPI types.
- `app/_features/linework/hooks` owns source import, size selection, physical settings, boundary review, cancellable analysis, and derived-PDF preparation.
- `app/_features/linework/components` owns the feature panel. It does not import unrelated feature modules.
- `app/api/linework/[...path]` forwards only known resources to the loopback Python engine. No external storage, account, or upload service is used.
- `services/engine` keeps the existing framework-free domain and separate PDF, geometry, application, storage, and HTTP modules. The old frontend is not embedded in the fork.
- `scripts` owns development orchestration, generated contracts, and the macOS desktop launcher. No machine-specific executable paths are committed; the installer discovers the current Node path.

## Projection integration

The engine produces a derived **vector PDF**, rather than drawing a screen-space offset over a calibrated canvas. The derivative uses native PDF physical coordinates, resolves the selected size, retains shared markings, and adds sewing/muslin boundaries and transferred notches. It then passes through the upstream viewer, stitching, calibration, rotation, and mirroring pipeline. Projector transforms therefore apply to the original and generated lines together.

The upstream transform/persistence key uses the source filename so generating linework does not create a different calibration identity. The original `File` remains untouched and can be restored. Prepared PDFs have resolved linework, so native size-layer editing is done after restoring the original. Settings changed after generation are explicitly marked pending. A file from a previously opened source is never reused for a new source.

The upstream Pattern Scale tool scales an entire PDF, including any allowance already drawn into it. For that reason, generation requires `1.00`; PDF correction is handled by the engine before offsetting. Changing Pattern Scale restores the original view. Mat/perspective calibration is independent and remains available.

## Upstream compatibility changes

The original public tree uses Next 13 and React-PDF 7. This fork uses the patched Next 15.5 line, current compatible React-PDF 10/PDF.js, next-intl 3.26, and Serwist 9 while retaining React 18. The old package patches were replaced by the custom renderer's explicit physical sizing. Page dimensions now come from PDF.js viewports so crop, rotation, and UserUnit are applied once. PDF loading is client-only; the minified PDF.js distribution avoids nested webpack module-scope collisions in development.

Locale routing passes its existing segment through a request header rather than rewriting a loopback URL back to itself. Font loading is local Input Mono. Upstream telemetry is removed. Native light/dark/green projection themes are preserved because they serve projection visibility.

Use narrowly scoped additions and merge upstream changes deliberately. Avoid a wholesale folder rename or redesign of the inherited calibration UI; that would make future merges harder without improving linework accuracy.

Patched PostCSS and Zod resolutions cover inherited Next/Serwist transitive dependencies; keep these overrides under review when updating those packages. The retained native stitching implementation now creates vector form objects before removing source pages, because current pdf-lib deletes detached page objects. Dedicated tests cover physical dimensions, vector retention, empty pages, and source-byte preservation. PDF text is escaped before entering the hover-label HTML renderer.
