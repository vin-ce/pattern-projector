from math import hypot
from pattern_engine.domain.models import Point

CURVE_TOLERANCE_MM = 0.02


def distance(a: Point, b: Point) -> float:
    return hypot(a[0] - b[0], a[1] - b[1])


def midpoint(a: Point, b: Point) -> Point:
    return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)


def cubic_points(
    p0: Point,
    p1: Point,
    p2: Point,
    p3: Point,
    tolerance: float = CURVE_TOLERANCE_MM,
    depth: int = 0,
) -> list[Point]:
    """Adaptive de Casteljau subdivision with a physical flatness bound."""
    length = distance(p0, p3)

    def deviation(p: Point) -> float:
        if length < 1e-12:
            return distance(p, p0)
        return (
            abs((p3[0] - p0[0]) * (p0[1] - p[1]) - (p0[0] - p[0]) * (p3[1] - p0[1]))
            / length
        )

    # Collinear controls outside the chord also require subdivision.
    excess = distance(p0, p1) + distance(p1, p2) + distance(p2, p3) - length
    if depth >= 24 or (
        max(deviation(p1), deviation(p2)) <= tolerance and excess <= tolerance
    ):
        return [p3]
    a, b, c = midpoint(p0, p1), midpoint(p1, p2), midpoint(p2, p3)
    d, e = midpoint(a, b), midpoint(b, c)
    f = midpoint(d, e)
    return cubic_points(p0, a, d, f, tolerance, depth + 1) + cubic_points(
        f, e, c, p3, tolerance, depth + 1
    )


def signed_area(points: list[Point]) -> float:
    return (
        sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(points, points[1:] + points[:1]))
        / 2
    )
