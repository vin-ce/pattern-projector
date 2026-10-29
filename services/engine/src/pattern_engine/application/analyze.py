from shapely.geometry import Polygon
from pattern_engine.domain.models import AnalysisRequest, Marking, PatternAnalysis
from pattern_engine.geometry.boundaries import detect_pieces
from pattern_engine.geometry.offsets import generate_piece
from pattern_engine.storage.projects import parsed, get_document


def analyze(document_id: str, request: AnalysisRequest) -> PatternAnalysis:
    pdf = parsed(document_id)
    document = get_document(document_id)
    if request.page > len(pdf.pages):
        raise ValueError("Page does not exist.")
    if document.sizes and request.size not in document.sizes:
        raise ValueError("Choose a size present in this PDF.")
    drawings = [d for d in pdf.drawings if d.page == request.page]
    pieces = detect_pieces(
        drawings,
        request.size,
        request.page,
        set(request.confirmed_piece_ids),
        set(request.excluded_piece_ids),
    )
    for piece in pieces:
        if piece.is_trouser:
            piece.hem_location = "bottom"
        x0, y0, x1, y1 = piece.bounds
        for page, anchor, allowance in pdf.top_hem_labels:
            if (
                page == piece.page
                and y0 - max(100, (y1 - y0) * 0.7) <= anchor[1] <= y0 + 15
                and x0 - (x1 - x0) * 0.6 <= anchor[0] <= x1 + (x1 - x0) * 0.6
            ):
                piece.hem_location = "top"
                piece.notices.append(
                    "Top-edge hem inferred from the nearby pattern label. Verify its location before cutting."
                )
    # Calibration rescales source geometry into corrected physical coordinates.
    scale = request.scale
    if scale != 1:
        for piece in pieces:
            piece.boundary = [(x * scale, y * scale) for x, y in piece.boundary]
            poly = Polygon(piece.boundary)
            piece.bounds = poly.bounds
            piece.area_mm2 = poly.area
    generated = []
    notices = []
    if request.generate:
        for piece in pieces:
            if piece.status != "ready":
                continue
            try:
                # Scale markings alongside boundaries, without mutating cached data.
                from dataclasses import replace

                marks = (
                    drawings
                    if scale == 1
                    else [
                        replace(
                            d,
                            subpaths=[
                                [(x * scale, y * scale) for x, y in path]
                                for path in d.subpaths
                            ],
                        )
                        for d in drawings
                    ]
                )
                use_hem = request.settings.preserve_hem and (
                    piece.hem_location is not None or piece.id in request.hem_piece_ids
                )
                generated.append(
                    generate_piece(piece, request.settings, marks, use_hem)
                )
            except ValueError as error:
                notices.append(f"{piece.name}: {error}")
        if any(piece.status in ("open", "review") for piece in pieces):
            notices.append(
                "Some boundaries need review. Generated lines cover ready pieces only."
            )
        if not generated:
            notices.append(
                "No sewing lines generated. Review boundaries or reduce the allowance."
            )
    boundary_ids = {path_id for piece in pieces for path_id in piece.source_path_ids}
    markings = [
        Marking(
            id=d.id,
            path=d.svg,
            width_mm=d.width_mm,
            dash_mm=d.dash_mm,
            fill=d.fill,
            stroke=d.stroke,
        )
        for d in drawings
        if d.layer == request.size and d.id not in boundary_ids
    ]
    source_paths = [
        Marking(
            id=d.id,
            path=d.svg,
            width_mm=d.width_mm,
            dash_mm=d.dash_mm,
            fill=d.fill,
            stroke=d.stroke,
        )
        for d in drawings
        if d.layer == request.size
    ]
    if pieces:
        boxes = [p.bounds for p in pieces]
        bounds = (
            min(b[0] for b in boxes),
            min(b[1] for b in boxes),
            max(b[2] for b in boxes),
            max(b[3] for b in boxes),
        )
    else:
        bounds = None
        notices.append("No supported piece boundaries found on this page.")
    return PatternAnalysis(
        pieces=pieces,
        generated=generated,
        markings=markings,
        source_paths=source_paths,
        bounds=bounds,
        notices=notices,
    )
