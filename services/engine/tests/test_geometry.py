import pytest
from shapely.geometry import LineString, Point, Polygon
from pattern_engine.domain.models import AllowanceSettings, Piece
from pattern_engine.geometry.curves import cubic_points
from pattern_engine.geometry.offsets import generate_piece, uniform_offset
from pattern_engine.pdf.reader import PageFrame
from pattern_engine.domain.paths import Drawing
from pattern_engine.geometry.boundaries import detect_pieces


def piece(points, **kwargs):
    p = Polygon(points)
    return Piece(
        id="fixture",
        name="Fixture",
        page=1,
        size="M",
        source_path_ids=[],
        boundary=points,
        bounds=p.bounds,
        area_mm2=p.area,
        status="ready",
        **kwargs,
    )


def test_three_eighths_inset_and_one_inch_muslin():
    source = piece([(0, 0), (200, 0), (200, 300), (0, 300)])
    result = generate_piece(source, AllowanceSettings(preserve_hem=False), [], False)
    assert Polygon(result.sewing).bounds == pytest.approx(
        (9.525, 9.525, 190.475, 290.475), abs=0.00001
    )
    assert Polygon(result.muslin).bounds == pytest.approx(
        (-15.875, -15.875, 215.875, 315.875), abs=0.00001
    )


def test_preserved_two_inch_hem_and_standard_side_seams():
    source = piece([(0, 0), (400, 0), (400, 1000), (0, 1000)], is_trouser=True)
    result = generate_piece(source, AllowanceSettings(), [], True)
    assert Polygon(result.sewing).bounds == pytest.approx(
        (9.525, 9.525, 390.475, 949.2), abs=0.00001
    )
    assert Polygon(result.muslin).bounds == pytest.approx(
        (-15.875, -15.875, 415.875, 1000), abs=0.00001
    )
    assert result.hem_applied


def test_confirmed_fold_has_no_added_allowance():
    source = piece([(0, 0), (200, 0), (200, 80), (0, 80)], fold_edge=True)
    result = generate_piece(source, AllowanceSettings(preserve_hem=False), [], False)
    assert Polygon(result.sewing).bounds == pytest.approx(
        (0, 9.525, 190.475, 70.475), abs=0.00001
    )
    assert Polygon(result.muslin).bounds == pytest.approx(
        (0, -15.875, 215.875, 95.875), abs=0.00001
    )


def test_pocket_top_hem_is_preserved():
    source = piece([(0, 0), (180, 0), (180, 220), (0, 220)], hem_location="top")
    result = generate_piece(source, AllowanceSettings(), [], True)
    assert Polygon(result.sewing).bounds == pytest.approx(
        (9.525, 50.8, 170.475, 210.475), abs=0.00001
    )
    assert Polygon(result.muslin).bounds == pytest.approx(
        (-15.875, 0, 195.875, 235.875), abs=0.00001
    )


def test_cubic_subdivision_physical_error_bound():
    p0, p1, p2, p3 = (0, 0), (0, 150), (200, -80), (200, 150)
    line = LineString([p0, *cubic_points(p0, p1, p2, p3)])
    errors = []
    for i in range(1001):
        t = i / 1000
        s = 1 - t
        p = Point(
            s**3 * p0[0] + 3 * s * s * t * p1[0] + 3 * s * t * t * p2[0] + t**3 * p3[0],
            s**3 * p0[1] + 3 * s * s * t * p1[1] + 3 * s * t * t * p2[1] + t**3 * p3[1],
        )
        errors.append(line.distance(p))
    assert max(errors) <= 0.020001


def test_collapse_does_not_return_a_plausible_boundary():
    with pytest.raises(ValueError):
        uniform_offset([(0, 0), (5, 0), (5, 20), (0, 20)], -9.525)


def test_zero_area_spur_cleanup_is_bounded_and_requires_fold_confirmation():
    points = [(200, 80), (200, 90), (200.0254, 90), (0, 90), (0, 0), (200, 0)]
    drawing = Drawing("spur", 1, "M", "1:0", [], [points], [False], True, 0.3)
    review = detect_pieces([drawing], "M", 1, set(), set())[0]
    assert review.status == "review"
    assert any("0.0254 mm" in note for note in review.notices)
    assert drawing.subpaths[0] == points
    confirmed = detect_pieces([drawing], "M", 1, {review.id}, set())[0]
    assert confirmed.status == "ready" and confirmed.fold_edge
    result = generate_piece(confirmed, AllowanceSettings(), [], False)
    assert max(x for x, y in result.muslin) == pytest.approx(200, abs=1e-6)


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_crop_user_unit_and_rotation_roundtrip(rotation):
    frame = PageFrame((10, 20, 410, 620), 2, rotation)
    for point in [(10, 20), (410, 620), (100, 400)]:
        assert frame.to_pdf(frame.to_mm(point)) == pytest.approx(point, abs=1e-9)
    assert frame.size == pytest.approx(
        (423.3333333333, 282.2222222222)
        if rotation in (90, 270)
        else (282.2222222222, 423.3333333333)
    )
