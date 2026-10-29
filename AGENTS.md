# Pattern Projector fork

Use the installed bulletproof-react skill for frontend additions.

- Preserve upstream project, calibration, transform, stitching, and layer behavior. Keep the MIT license and copyright notice.
- New domain features live in app/_features/<feature> with concrete imports; compose them in app/[locale]/calibrate/page.tsx. Avoid rearranging upstream files just to match a template.
- No sibling feature imports. Shared upstream primitives remain in app/_components and app/_lib.
- Python PDF parsing, physical geometry, storage, and transport stay in services/engine's separate modules. Originals are immutable; uncertain contours require explicit confirmation.
- app/_features/linework/api/schema.ts is generated from the engine OpenAPI schema.
- Keep Input Mono, monochrome surfaces, square corners, and concise user-facing controls. Retain useful upstream projection themes.
- Run yarn check, yarn test:unit --runInBand, yarn build, and Python tests for relevant changes.
- End user-facing messages with concise Dev links to verified current development addresses. Label stopped or unverified servers.
