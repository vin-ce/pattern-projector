# Accuracy and supported inputs

## Source and generated geometry

The original PDF is never rewritten. Size selection uses actual optional-content groups; repeated layer names are kept as distinct PDF object identities. The display and export use the same generated point lists.

Supported path operators include lines, rectangles, cubic Bezier curves, shorthand cubic curves, and closed paths, with nested graphics-state and form transforms. Page rotation, CropBox origins, and UserUnit are normalized to millimetres.

Original vector commands are preserved for display and source export. Generated offsets use adaptive cubic subdivision with a 0.02 mm flatness criterion. Clipper2 uses an integer scale of 1,000,000 per millimetre. These settings describe computational geometry, not physical projector/printer accuracy or a complete end-to-end error guarantee.

The automated tests check curve deviation, known offset distances, two-inch hems, zero-allowance folds, crop/rotation/unit conversion, calibration references, saved state, and vector measurements after export.

## Interpretation

Closed size-specific contours can be offset directly. Split paths join automatically only when endpoints agree within 0.1 mm. Nearly straight open markings are excluded from boundary candidates. Open outlines and inferred folds require explicit confirmation. The straight closure is a proposal to inspect, not a reconstruction of missing original curve information.

A zero-area spur may be removed from the calculation copy only if exactly one polygon remains and its maximum boundary deviation is at most 0.05 mm. The result records the measured deviation. Other self-intersections are not silently repaired.

Long leg panels receive bottom-hem treatment when enabled. Nearby explicit `Top edge` allowance labels can identify pocket top hems; verify these inferred assignments in the piece review. The current settings apply one entered hem width to the identified hem edges. Arbitrary edge-by-edge editing is a future feature.

Only inferred vertical straight fold edges currently receive zero-allowance treatment. Geometry that splits, collapses, or fails containment validation is reported instead of generating a plausible replacement. Notches are transferred by local boundary normals; original markings remain available and should be compared before cutting.

## Calibration

The importer recognizes approximately axis-aligned two-inch and five-centimetre reference squares in calibration layers. A verification pass requires both dimensions to agree within 0.1 mm. Failure to detect a reference does not prove scale is wrong; use a known length and the manual uniform correction.

Display zoom is independent of document scale. Export preserves physical distances and expands page bounds when needed. Verify printed output at Actual size / 100%. Projectors require their own cutting-surface calibration; this first version does not implement projector alignment.

## Limitations

Scanned PDFs require tracing and are not supported for automatic size or boundary extraction. PDFs without size layers can be viewed and reviewed, but size isolation is unavailable. Complex optional-content visibility expressions, unusual clipping, and overlapping compound outlines may require conversion or manual interpretation. General curve/node editing, size grading, projector calibration, and tiled home-printer export are not included in this version.
