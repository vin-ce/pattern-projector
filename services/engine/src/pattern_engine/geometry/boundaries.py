from shapely.geometry import LineString, Polygon
from shapely import make_valid
from pattern_engine.domain.models import Piece
from pattern_engine.geometry.curves import distance
from pattern_engine.domain.paths import Drawing


def clean_points(points):
    result = []
    for point in points:
        if not result or distance(point, result[-1]) > 0.00001:
            result.append(point)
    if len(result) > 2 and distance(result[0], result[-1]) < 0.00001:
        result.pop()
    return result


def detect_pieces(
    drawings: list[Drawing],
    size: str | None,
    page: int,
    confirmed: set[str],
    excluded: set[str],
) -> list[Piece]:
    paths = []
    for drawing in drawings:
        if drawing.page != page or not drawing.stroke:
            continue
        if size is not None and drawing.layer != size:
            continue
        if (
            size is None
            and drawing.layer
            and any(
                word in drawing.layer.lower()
                for word in ("grid", "calibrat", "title", "chart", "background")
            )
        ):
            continue
        for index, (points, closed) in enumerate(zip(drawing.subpaths, drawing.closed)):
            points = clean_points(points)
            if len(points) < 3 or LineString(points).length < 60:
                continue
            xs, ys = zip(*points)
            if max(max(xs) - min(xs), max(ys) - min(ys)) < 40:
                continue
            if (
                not closed
                and LineString(points).length < distance(points[0], points[-1]) * 1.1
            ):
                continue
            paths.append(
                {
                    "points": points,
                    "closed": closed or distance(points[0], points[-1]) <= 0.1,
                    "ids": [drawing.id],
                    "suffix": index,
                }
            )

    # Reconstruct outlines split across strokes only when their endpoints agree
    # within 0.1 mm. Larger gaps remain explicit review candidates.
    changed = True
    while changed:
        changed = False
        for i, a in enumerate(paths):
            if a["closed"]:
                continue
            for j in range(i + 1, len(paths)):
                b = paths[j]
                if b["closed"]:
                    continue
                pa, pb = a["points"], b["points"]
                joined = None
                for aa, bb in (
                    (pa, pb),
                    (pa, list(reversed(pb))),
                    (list(reversed(pa)), pb),
                    (list(reversed(pa)), list(reversed(pb))),
                ):
                    if distance(aa[-1], bb[0]) <= 0.1:
                        joined = aa + bb[1:]
                        break
                if joined:
                    a["points"] = joined
                    a["ids"] += b["ids"]
                    a["closed"] = distance(joined[0], joined[-1]) <= 0.1
                    paths.pop(j)
                    changed = True
                    break
            if changed:
                break

    pieces = []
    for path in paths:
        points = clean_points(path["points"])
        polygon = Polygon(points)
        if polygon.area < 150:
            continue
        x0, y0, x1, y1 = polygon.bounds
        w, h = x1 - x0, y1 - y0
        piece_id = f"{path['ids'][0]}:{path['suffix']}"
        fold = (
            not path["closed"]
            and abs(points[0][0] - points[-1][0]) <= 0.2
            and abs(points[0][1] - points[-1][1]) > 20
            and w > h * 1.5
        )
        cleanup_note = None
        if not polygon.is_valid:
            repaired = make_valid(polygon)
            parts = list(repaired.geoms) if hasattr(repaired, "geoms") else [repaired]
            polygons = [part for part in parts if part.geom_type == "Polygon"]
            if len(polygons) == 1 and all(
                part.area == 0 for part in parts if part.geom_type != "Polygon"
            ):
                deviation = polygon.boundary.hausdorff_distance(polygons[0].boundary)
                if deviation <= 0.05:
                    polygon = polygons[0]
                    points = clean_points(list(polygon.exterior.coords))
                    cleanup_note = f"A zero-area path spur was removed for calculation (maximum change {deviation:.4f} mm). The source PDF is unchanged."
        status = (
            "ready"
            if path["closed"] and polygon.is_valid
            else "review"
            if fold
            else "open"
        )
        notes = []
        if cleanup_note:
            notes.append(cleanup_note)
        if not polygon.is_valid:
            notes.append(
                "Boundary intersects itself. Offsets are disabled until corrected."
            )
        if fold:
            notes.append(
                "Confirmed fold edge; zero allowance on this edge."
                if piece_id in confirmed
                else "Open edge appears to be a fold. Confirm to close it with zero allowance on that edge."
            )
        elif not path["closed"]:
            notes.append(
                "Incomplete outline. Confirm a straight closing edge only if it matches the pattern."
            )
        if size is None and status == "ready":
            status = "review"
            notes.append(
                "No size metadata. Confirm this boundary before generating lines."
            )
        if piece_id in confirmed and polygon.is_valid:
            status = "ready"
        if piece_id in excluded:
            status = "excluded"
        trouser = h > 500 and w > 150
        name = (
            "Leg panel"
            if trouser
            else "Waistband"
            if fold
            else "Pocket"
            if h > w * 0.9 and h < 450
            else "Pattern piece"
        )
        pieces.append(
            Piece(
                id=piece_id,
                name=name,
                page=page,
                size=size,
                source_path_ids=path["ids"],
                boundary=points,
                bounds=polygon.bounds,
                area_mm2=polygon.area,
                status=status,
                is_trouser=trouser,
                fold_edge=fold,
                can_confirm=polygon.is_valid,
                notices=notes,
            )
        )
    pieces.sort(key=lambda p: (round(p.bounds[1] / 30), p.bounds[0]))
    counts = {}
    for piece in pieces:
        counts[piece.name] = counts.get(piece.name, 0) + 1
        piece.name = f"{piece.name} {counts[piece.name]:02d}"
    return pieces
