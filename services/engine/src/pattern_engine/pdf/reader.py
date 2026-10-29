"""Interpret supported PDF path operators without changing the source document.

Coordinates exposed to the app are top-left-origin physical millimetres, after
page units, CropBox, rotation, and nested form/graphics-state transformations.
"""

from dataclasses import dataclass, field
from fractions import Fraction
from math import hypot
from pathlib import Path
import re
import pikepdf
from pypdf import PdfReader
from pattern_engine.domain.models import CalibrationReference, Layer, PageInfo, Point
from pattern_engine.geometry.curves import cubic_points
from pattern_engine.domain.paths import Drawing

MM_PER_PT = 25.4 / 72
IDENTITY = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
SIZE_RE = re.compile(
    r"^(?:size\s*)?(?:[2-9]?XS|S|M|L|[2-9]?XL|XXS|XXL|XXXL|\d{1,3})$", re.I
)


def layer_kind(name: str) -> str:
    if SIZE_RE.fullmatch(name.strip()):
        return "size"
    if "grid" in name.lower():
        return "grid"
    if "background" in name.lower():
        return "background"
    return "shared"


def matrix_multiply(m, n):
    a, b, c, d, e, f = m
    A, B, C, D, E, F = n
    return (
        a * A + c * B,
        b * A + d * B,
        a * C + c * D,
        b * C + d * D,
        a * E + c * F + e,
        b * E + d * F + f,
    )


def transform(m, x, y) -> Point:
    a, b, c, d, e, f = m
    return (a * float(x) + c * float(y) + e, b * float(x) + d * float(y) + f)


@dataclass
class PageFrame:
    box: tuple[float, float, float, float]
    unit: float
    rotation: int

    @property
    def native_size(self):
        x0, y0, x1, y1 = self.box
        return ((x1 - x0) * self.unit * MM_PER_PT, (y1 - y0) * self.unit * MM_PER_PT)

    @property
    def size(self):
        w, h = self.native_size
        return (h, w) if self.rotation in (90, 270) else (w, h)

    def to_mm(self, point: Point) -> Point:
        x = (point[0] - self.box[0]) * self.unit * MM_PER_PT
        y = (point[1] - self.box[1]) * self.unit * MM_PER_PT
        w, h = self.native_size
        return {0: (x, h - y), 90: (y, x), 180: (w - x, y), 270: (h - y, w - x)}[
            self.rotation
        ]

    def to_pdf(self, point: Point) -> Point:
        u, v = point
        w, h = self.native_size
        x, y = {0: (u, h - v), 90: (v, u), 180: (w - u, v), 270: (w - v, h - u)}[
            self.rotation
        ]
        return (
            x / (self.unit * MM_PER_PT) + self.box[0],
            y / (self.unit * MM_PER_PT) + self.box[1],
        )


@dataclass
class ParsedPDF:
    pages: list[PageInfo]
    frames: list[PageFrame]
    layers: list[Layer]
    drawings: list[Drawing]
    calibration: list[CalibrationReference]
    seam_mm: float | None
    hem_mm: float | None
    notices: list[str] = field(default_factory=list)
    top_hem_labels: list[tuple[int, Point, float]] = field(default_factory=list)


def read_pdf(path: Path) -> ParsedPDF:
    drawings = []
    pages = []
    frames = []
    layers = []
    notices = []
    with pikepdf.open(path) as pdf:
        oc = pdf.Root.get("/OCProperties", {})
        config = oc.get("/D", {})
        off = {obj.objgen for obj in config.get("/OFF", [])}
        on = {obj.objgen for obj in config.get("/ON", [])}
        for obj in oc.get("/OCGs", []):
            name = str(obj.get("/Name", "Unnamed layer"))
            visible = obj.objgen not in off and (
                str(config.get("/BaseState", "/ON")) != "/OFF" or obj.objgen in on
            )
            layers.append(
                Layer(
                    id=f"{obj.objgen[0]}:{obj.objgen[1]}",
                    name=name,
                    kind=layer_kind(name),
                    visible=visible,
                )
            )

        for page_number, page in enumerate(pdf.pages, 1):
            box = tuple(
                float(v) for v in page.obj.get("/CropBox", page.obj["/MediaBox"])
            )
            rotation = int(page.obj.get("/Rotate", 0)) % 360
            if rotation not in (0, 90, 180, 270):
                raise ValueError("Unsupported page rotation.")
            frame = PageFrame(box, float(page.obj.get("/UserUnit", 1)), rotation)
            frames.append(frame)
            w, h = frame.size
            pages.append(
                PageInfo(number=page_number, width_mm=w, height_mm=h, rotation=rotation)
            )

            def walk(
                stream,
                resources,
                key,
                initial_matrix=IDENTITY,
                inherited_layers=(),
                depth=0,
            ):
                if depth > 20:
                    raise ValueError("PDF form nesting exceeds the supported limit.")
                state = {"matrix": initial_matrix, "width": 1.0, "dash": []}
                saved = []
                optional = list(inherited_layers)
                commands = []
                subpaths = []
                closed = []
                current = None
                start = None

                def point(x, y):
                    return frame.to_mm(transform(state["matrix"], x, y))

                for index, (operands, operator) in enumerate(
                    pikepdf.parse_content_stream(stream)
                ):
                    op = str(operator)
                    if op == "q":
                        saved.append(state.copy())
                    elif op == "Q":
                        if saved:
                            state = saved.pop()
                    elif op == "cm":
                        state["matrix"] = matrix_multiply(
                            state["matrix"], tuple(map(float, operands))
                        )
                    elif op == "w":
                        state["width"] = float(operands[0])
                    elif op == "d":
                        state["dash"] = list(map(float, operands[0]))
                    elif op in ("BDC", "BMC"):
                        group = None
                        if op == "BDC" and str(operands[0]) == "/OC":
                            prop = operands[1]
                            if isinstance(prop, pikepdf.Name):
                                prop = resources.get("/Properties", {}).get(prop)
                            if prop is not None and prop.get("/Type") == pikepdf.Name(
                                "/OCG"
                            ):
                                group = (
                                    str(prop.get("/Name", "")),
                                    f"{prop.objgen[0]}:{prop.objgen[1]}",
                                )
                            else:
                                notices.append(
                                    "A complex layer membership needs review; size filtering may be incomplete."
                                )
                        optional.append(group)
                    elif op == "EMC":
                        if optional:
                            optional.pop()
                    elif op == "m":
                        current = point(*operands)
                        start = current
                        commands.append(("M", current))
                        subpaths.append([current])
                        closed.append(False)
                    elif op == "l" and current is not None:
                        current = point(*operands)
                        commands.append(("L", current))
                        subpaths[-1].append(current)
                    elif op in ("c", "v", "y") and current is not None:
                        if op == "c":
                            p1, p2, p3 = (
                                point(*operands[:2]),
                                point(*operands[2:4]),
                                point(*operands[4:6]),
                            )
                        elif op == "v":
                            p1, p2, p3 = (
                                current,
                                point(*operands[:2]),
                                point(*operands[2:4]),
                            )
                        else:
                            p1, p3 = point(*operands[:2]), point(*operands[2:4])
                            p2 = p3
                        commands.append(("C", p1, p2, p3))
                        subpaths[-1].extend(cubic_points(current, p1, p2, p3))
                        current = p3
                    elif op == "re":
                        x, y, rw, rh = map(float, operands)
                        pts = [
                            point(x, y),
                            point(x + rw, y),
                            point(x + rw, y + rh),
                            point(x, y + rh),
                        ]
                        commands.extend(
                            [("M", pts[0]), *[("L", p) for p in pts[1:]], ("Z",)]
                        )
                        subpaths.append(pts)
                        closed.append(True)
                        current = pts[0]
                        start = current
                    elif op == "h" and current is not None:
                        commands.append(("Z",))
                        closed[-1] = True
                        current = start
                    elif op in ("S", "s", "f", "F", "f*", "B", "B*", "b", "b*", "n"):
                        if op in ("s", "b", "b*") and subpaths:
                            commands.append(("Z",))
                            closed[-1] = True
                        if commands and op != "n":
                            layer = next((g for g in reversed(optional) if g), None)
                            a, b, c, d, _, _ = state["matrix"]
                            line_scale = max(hypot(a, b), hypot(c, d))
                            drawings.append(
                                Drawing(
                                    f"{key}:{index}",
                                    page_number,
                                    layer[0] if layer else None,
                                    layer[1] if layer else None,
                                    commands,
                                    subpaths,
                                    closed,
                                    op in ("S", "s", "B", "B*", "b", "b*"),
                                    state["width"]
                                    * line_scale
                                    * frame.unit
                                    * MM_PER_PT,
                                    [
                                        value * line_scale * frame.unit * MM_PER_PT
                                        for value in state["dash"]
                                    ],
                                    op in ("f", "F", "f*", "B", "B*", "b", "b*"),
                                )
                            )
                        commands = []
                        subpaths = []
                        closed = []
                        current = None
                        start = None
                    elif op == "Do":
                        obj = resources.get("/XObject", {}).get(operands[0])
                        if obj is not None and obj.get("/Subtype") == pikepdf.Name(
                            "/Form"
                        ):
                            inherited = list(optional)
                            group = obj.get("/OC")
                            if group and group.get("/Type") == pikepdf.Name("/OCG"):
                                inherited.append(
                                    (
                                        str(group.get("/Name", "")),
                                        f"{group.objgen[0]}:{group.objgen[1]}",
                                    )
                                )
                            mat = matrix_multiply(
                                state["matrix"],
                                tuple(map(float, obj.get("/Matrix", IDENTITY))),
                            )
                            walk(
                                obj,
                                obj.get("/Resources", resources),
                                f"{key}/{operands[0]}@{index}",
                                mat,
                                inherited,
                                depth + 1,
                            )

            walk(page, page.obj.get("/Resources", {}), f"p{page_number}")

    for layer in layers:
        stroke = next(
            (d for d in drawings if d.layer_id == layer.id and d.stroke), None
        )
        if stroke:
            layer.dash_mm = stroke.dash_mm
    calibration = []
    for drawing in drawings:
        if not drawing.layer or "calibrat" not in drawing.layer.lower():
            continue
        for points, is_closed in zip(drawing.subpaths, drawing.closed):
            if not is_closed or len(points) != 4:
                continue
            xs, ys = zip(*points)
            w = max(xs) - min(xs)
            h = max(ys) - min(ys)
            expected = min((50.0, 50.8), key=lambda value: abs(w - value))
            if abs(w - expected) < 3 and abs(w - h) < 3:
                error = max(abs(w - expected), abs(h - expected))
                calibration.append(
                    CalibrationReference(
                        label="2 × 2 in" if expected == 50.8 else "5 × 5 cm",
                        width_mm=w,
                        height_mm=h,
                        expected_mm=expected,
                        error_mm=error,
                        verified=error <= 0.1,
                    )
                )
    seam = None
    hem = None
    top_hem_labels = []
    try:
        reader = PdfReader(path)
        text_parts = []
        for page_index, page in enumerate(reader.pages):

            def visitor(value, cm, tm, font, font_size):
                match = re.search(r'Top edge\s+(\d+(?:/\d+)?)\s*[”"″]', value, re.I)
                if match:
                    anchor = frames[page_index].to_mm(transform(cm, tm[4], tm[5]))
                    top_hem_labels.append(
                        (page_index + 1, anchor, float(Fraction(match[1])) * 25.4)
                    )

            text_parts.append(page.extract_text(visitor_text=visitor)[:200000])
        text = "\n".join(text_parts)
        match = re.search(r'Seam allowance\s+(\d+(?:/\d+)?)\s*[”"″]', text, re.I)
        if match:
            seam = float(Fraction(match[1])) * 25.4
        match = re.search(r'(?:Hem|Top edge)\s+(\d+(?:/\d+)?)\s*[”"″]', text, re.I)
        if match:
            hem = float(Fraction(match[1])) * 25.4
    except Exception:
        notices.append(
            "Allowance text could not be read. Check the pattern instructions."
        )
    if not calibration:
        notices.append(
            "No supported calibration squares detected. Verify scale with a known measurement."
        )
    if not layers:
        notices.append(
            "This PDF has no size layers. All vector paths are available for boundary review; size isolation is unavailable."
        )
    if not any(drawing.stroke for drawing in drawings):
        notices.append(
            "No editable vector outlines found. Scanned patterns require tracing and are not supported yet."
        )
    return ParsedPDF(
        pages,
        frames,
        layers,
        drawings,
        calibration,
        seam,
        hem,
        list(dict.fromkeys(notices)),
        top_hem_labels,
    )
