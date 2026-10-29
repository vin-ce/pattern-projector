"""Clipper2 uniform offsets and explicit edge-specific allowance joins."""

from math import hypot
import numpy as np
import pyclipr
from shapely.geometry import LineString, Point as ShapelyPoint, Polygon
from shapely.geometry.polygon import orient
from shapely import affinity
from shapely.ops import unary_union
from pattern_engine.domain.models import AllowanceSettings, GeneratedPiece, Piece, Point
from pattern_engine.geometry.curves import distance, signed_area
from pattern_engine.domain.paths import Drawing


def uniform_offset(points: list[Point], delta: float) -> list[Point]:
    if abs(delta) < 0.000001:
        return points[:]
    clip = pyclipr.ClipperOffset()
    clip.scaleFactor = 1_000_000
    clip.miterLimit = 5
    clip.arcTolerance = 0.005
    polygon = orient(Polygon(points), sign=1.0)
    clip.addPath(
        np.array(polygon.exterior.coords[:-1]),
        pyclipr.JoinType.Miter,
        pyclipr.EndType.Polygon,
    )
    paths = clip.execute(delta)
    if len(paths) != 1:
        raise ValueError(
            "This allowance splits or collapses the piece. Reduce the allowance or review the boundary."
        )
    result = [(float(p[0]), float(p[1])) for p in paths[0]]
    if len(result) < 3 or Polygon(result).area < 1:
        raise ValueError("This allowance removes the entire piece.")
    return result


def edge_offset(points: list[Point], deltas: list[float]) -> list[Point]:
    """Intersect adjacent displaced segments for straight hem/fold transitions.

    Curve segments all share the same allowance. Reject topology changes rather
    than silently repairing a potentially meaningful pattern feature.
    """
    if max(deltas) - min(deltas) < 1e-7:
        return uniform_offset(points, deltas[0])
    ccw = signed_area(points) > 0
    segments = []
    for i, (a, b) in enumerate(zip(points, points[1:] + points[:1])):
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = hypot(dx, dy)
        if length < 1e-9:
            raise ValueError("Duplicate boundary vertices require review.")
        nx, ny = (dy / length, -dx / length) if ccw else (-dy / length, dx / length)
        delta = deltas[i]
        segments.append(
            (
                (a[0] + nx * delta, a[1] + ny * delta),
                (b[0] + nx * delta, b[1] + ny * delta),
            )
        )
    result = []
    for i, (c, d) in enumerate(segments):
        a, b = segments[i - 1]
        rx, ry = b[0] - a[0], b[1] - a[1]
        sx, sy = d[0] - c[0], d[1] - c[1]
        cross = rx * sy - ry * sx
        if abs(cross) < 1e-10:
            if distance(b, c) > 0.05:
                raise ValueError(
                    "Adjacent parallel edges have incompatible allowances."
                )
            result.append(((b[0] + c[0]) / 2, (b[1] + c[1]) / 2))
            continue
        t = ((c[0] - a[0]) * sy - (c[1] - a[1]) * sx) / cross
        p = (a[0] + t * rx, a[1] + t * ry)
        if distance(p, points[i]) > max(abs(deltas[i]), abs(deltas[i - 1]), 0.1) * 6:
            # A bounded bevel prevents needles at very acute offset corners.
            result.extend([b, c])
        else:
            result.append(p)
    poly = Polygon(result)
    if not poly.is_valid:
        clip = pyclipr.Clipper()
        clip.scaleFactor = 1_000_000
        clip.addPath(np.array(result), pyclipr.PathType.Subject)
        paths = clip.execute(pyclipr.ClipType.Union, pyclipr.FillRule.NonZero)
        if len(paths) != 1:
            raise ValueError(
                "Edge-specific allowances split this piece. Review the hem/fold settings."
            )
        result = [(float(p[0]), float(p[1])) for p in paths[0]]
        poly = Polygon(result)
    if not poly.is_valid or poly.area < 1:
        raise ValueError(
            "Edge-specific allowances intersect or collapse here. Review the hem/fold settings."
        )
    return result


def hem_edges(points: list[Point], location="bottom") -> set[int]:
    x0, y0, x1, y1 = Polygon(points).bounds
    candidates = []
    for i, (a, b) in enumerate(zip(points, points[1:] + points[:1])):
        dx, dy = abs(b[0] - a[0]), abs(b[1] - a[1])
        near_edge = (
            min(a[1], b[1]) > y1 - (y1 - y0) * 0.12
            if location == "bottom"
            else max(a[1], b[1]) < y0 + (y1 - y0) * 0.12
        )
        if dx > 20 and dy / max(dx, 0.001) < 0.4 and near_edge:
            candidates.append((i, (a[1] + b[1]) / 2))
    if not candidates:
        return set()
    extreme = (
        max(value for _, value in candidates)
        if location == "bottom"
        else min(value for _, value in candidates)
    )
    return {i for i, value in candidates if abs(extreme - value) < 50}


def clip_inward(
    points: list[Point],
    edges: list[tuple[Point, Point]],
    distance_mm: float,
    reference: list[Point],
) -> list[Point]:
    poly = Polygon(points)
    ccw = signed_area(reference) > 0
    extent = max(Polygon(reference).bounds[2:]) + 10000
    for a, b in edges:
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = hypot(dx, dy)
        tx, ty = dx / length, dy / length
        nx, ny = (-ty, tx) if ccw else (ty, -tx)
        p = (
            a[0] + nx * distance_mm - tx * extent,
            a[1] + ny * distance_mm - ty * extent,
        )
        q = (
            b[0] + nx * distance_mm + tx * extent,
            b[1] + ny * distance_mm + ty * extent,
        )
        half = Polygon(
            [
                p,
                q,
                (q[0] + nx * extent, q[1] + ny * extent),
                (p[0] + nx * extent, p[1] + ny * extent),
            ]
        )
        poly = poly.intersection(half)
    if poly.geom_type != "Polygon" or poly.is_empty or poly.interiors:
        raise ValueError("The hem or fold rule splits this piece.")
    return [(float(x), float(y)) for x, y in poly.exterior.coords[:-1]]


def offset_with_fold(
    points: list[Point],
    delta: float,
    fold_line: tuple[Point, Point] | None,
    reference: list[Point],
) -> list[Point]:
    if fold_line is None:
        return uniform_offset(points, delta)
    a, b = fold_line
    if abs(a[0] - b[0]) > 0.2:
        raise ValueError("Only straight vertical inferred fold edges are supported.")
    x = (a[0] + b[0]) / 2
    poly = Polygon(points)
    reflected = affinity.scale(poly, xfact=-1, yfact=1, origin=(x, 0))
    combined = unary_union([poly, reflected])
    if combined.geom_type != "Polygon":
        raise ValueError("Fold edge does not join cleanly. Review the closing edge.")
    expanded = uniform_offset(list(combined.exterior.coords[:-1]), delta)
    return clip_inward(expanded, [fold_line], 0, reference)


def generate_piece(
    piece: Piece, settings: AllowanceSettings, drawings: list[Drawing], use_hem: bool
) -> GeneratedPiece:
    points = piece.boundary
    if not Polygon(points).is_valid:
        raise ValueError("The source boundary intersects itself.")
    hems = hem_edges(points, piece.hem_location or "bottom") if use_hem else set()
    if use_hem and not hems:
        raise ValueError("A straight hem edge could not be identified.")
    fold_line = (points[-1], points[0]) if piece.fold_edge else None
    sewing = offset_with_fold(points, -settings.seam_mm, fold_line, points)
    original_hems = [(points[i], points[(i + 1) % len(points)]) for i in hems]
    if hems:
        if settings.hem_mm < settings.seam_mm:
            raise ValueError(
                "The hem must be at least as wide as the standard seam allowance."
            )
        sewing = clip_inward(sewing, original_hems, settings.hem_mm, points)
    muslin_base = sewing
    if hems and settings.hem_mm > settings.muslin_mm:
        # Extend only the long, straight hem edges before a robust uniform
        # Clipper offset. Curved edges are never displaced with a naive miter.
        deltas = []
        for a, b in zip(sewing, sewing[1:] + sewing[:1]):
            midpoint = ShapelyPoint((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            dx, dy = b[0] - a[0], b[1] - a[1]
            length = hypot(dx, dy)

            def matches(edge):
                c, d = edge
                ex, ey = d[0] - c[0], d[1] - c[1]
                return (
                    abs(dx * ey - dy * ex) / max(length * hypot(ex, ey), 1e-9) < 0.002
                    and abs(LineString(edge).distance(midpoint) - settings.hem_mm) < 0.1
                )

            deltas.append(
                settings.hem_mm - settings.muslin_mm
                if any(matches(edge) for edge in original_hems)
                else 0
            )
        muslin_base = edge_offset(sewing, deltas)
    muslin = offset_with_fold(muslin_base, settings.muslin_mm, fold_line, points)
    if hems:
        muslin = clip_inward(muslin, original_hems, 0, points)
    seam_poly = Polygon(sewing)
    cut_poly = Polygon(muslin)
    source_poly = Polygon(points)
    if not source_poly.buffer(0.03).covers(seam_poly):
        raise ValueError("The sewing boundary leaves the original piece.")
    if not cut_poly.buffer(0.03).covers(seam_poly):
        raise ValueError("The cutting boundary does not contain the sewing boundary.")
    source_edge = source_poly.exterior
    cut_edge = cut_poly.exterior
    notches = []
    anchors = []
    for drawing in drawings:
        if drawing.layer != piece.size or drawing.id in piece.source_path_ids:
            continue
        for path in drawing.subpaths:
            if len(path) < 2:
                continue
            mark = LineString(path)
            if not 1 <= mark.length <= 13:
                continue
            endpoint = min(
                (path[0], path[-1]), key=lambda p: source_edge.distance(ShapelyPoint(p))
            )
            if source_edge.distance(ShapelyPoint(endpoint)) > 1.5:
                continue
            t = source_edge.project(ShapelyPoint(endpoint))
            anchor = source_edge.interpolate(t)
            if any(anchor.distance(old) < 2 for old in anchors):
                continue
            anchors.append(anchor)
            # Derive a local normal from the original seam position. Trace that
            # normal to the new cut edge rather than using an arbitrary vertex.
            before = source_edge.interpolate(max(0, t - 0.2))
            after = source_edge.interpolate(min(source_edge.length, t + 0.2))
            dx, dy = after.x - before.x, after.y - before.y
            l = hypot(dx, dy)
            if l < 1e-8:
                continue
            nx, ny = dy / l, -dx / l
            probe = ShapelyPoint(anchor.x + nx * 0.5, anchor.y + ny * 0.5)
            if source_poly.contains(probe):
                nx, ny = -nx, -ny
            ray = LineString(
                [
                    (anchor.x - nx * 200, anchor.y - ny * 200),
                    (anchor.x + nx * 200, anchor.y + ny * 200),
                ]
            )
            crossings = cut_edge.intersection(ray)
            options = (
                list(crossings.geoms) if hasattr(crossings, "geoms") else [crossings]
            )
            options = [p for p in options if p.geom_type == "Point"]
            if not options:
                continue
            target = min(options, key=lambda p: p.distance(anchor))
            notches.append(
                [(target.x, target.y), (target.x - nx * 3, target.y - ny * 3)]
            )
    return GeneratedPiece(
        piece_id=piece.id,
        sewing=sewing,
        muslin=muslin,
        notches=notches,
        hem_applied=bool(hems),
    )
