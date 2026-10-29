from io import BytesIO
from pathlib import Path
import pikepdf
from pattern_engine.domain.models import ExportRequest, PatternAnalysis
from pattern_engine.pdf.reader import MM_PER_PT, PageFrame, layer_kind


def write_pdf(
    source: Path, request: ExportRequest, analyses: list[PatternAnalysis]
) -> bytes:
    """Flatten excluded content without discarding graphics-state instructions."""
    with pikepdf.open(source) as pdf:

        def visible(group):
            if group is None:
                return True
            if group.get("/Type") == pikepdf.Name("/OCMD"):
                if group.get("/VE") is not None:
                    raise ValueError(
                        "This PDF uses complex layer visibility expressions. Export is unsupported."
                    )
                groups = group.get("/OCGs", [])
                if isinstance(groups, pikepdf.Dictionary):
                    groups = [groups]
                values = [visible(g) for g in groups]
                policy = str(group.get("/P", "/AnyOn"))
                return {
                    "/AnyOn": any(values),
                    "/AllOn": all(values),
                    "/AnyOff": any(not v for v in values),
                    "/AllOff": all(not v for v in values),
                }.get(policy, True)
            name = str(group.get("/Name", ""))
            return name not in request.hidden_layer_names and (
                layer_kind(name) != "size" or name == request.size
            )

        for page_number, page in enumerate(pdf.pages, 1):
            analysis = analyses[page_number - 1]
            skip_ids = (
                {id for piece in analysis.pieces for id in piece.source_path_ids}
                if not request.include_original
                else set()
            )
            visited = set()

            def flatten(stream, resources, key, inherited_hidden=False):
                instructions = []
                marked = []
                for index, (args, operator) in enumerate(
                    pikepdf.parse_content_stream(stream)
                ):
                    op = str(operator)
                    hidden = inherited_hidden or any(item[1] for item in marked)
                    if op in ("BDC", "BMC"):
                        is_optional = op == "BDC" and str(args[0]) == "/OC"
                        group = None
                        if is_optional:
                            group = args[1]
                            if isinstance(group, pikepdf.Name):
                                group = resources.get("/Properties", {}).get(group)
                        marked.append((is_optional, is_optional and not visible(group)))
                        if not is_optional:
                            instructions.append((args, operator))
                        continue
                    if op == "EMC":
                        tag = marked.pop() if marked else (False, False)
                        if not tag[0]:
                            instructions.append((args, operator))
                        continue
                    if op in ("S", "s", "f", "F", "f*", "B", "B*", "b", "b*") and (
                        hidden or f"{key}:{index}" in skip_ids
                    ):
                        instructions.append(([], pikepdf.Operator("n")))
                        continue
                    if hidden and op in ("Tj", "TJ"):
                        continue
                    if hidden and op == "'":
                        instructions.append(([], pikepdf.Operator("T*")))
                        continue
                    if hidden and op == '"':
                        instructions.extend(
                            [
                                ([args[0]], pikepdf.Operator("Tw")),
                                ([args[1]], pikepdf.Operator("Tc")),
                                ([], pikepdf.Operator("T*")),
                            ]
                        )
                        continue
                    if op == "Do":
                        obj = resources.get("/XObject", {}).get(args[0])
                        if hidden or (obj is not None and not visible(obj.get("/OC"))):
                            continue
                        if (
                            obj is not None
                            and obj.get("/Subtype") == pikepdf.Name("/Form")
                            and obj.objgen not in visited
                        ):
                            visited.add(obj.objgen)
                            data = flatten(
                                obj,
                                obj.get("/Resources", resources),
                                f"{key}/{args[0]}@{index}",
                            )
                            obj.write(data)
                            if "/OC" in obj:
                                del obj["/OC"]
                    if request.monochrome and op in ("K", "RG", "G"):
                        instructions.append(([0], pikepdf.Operator("G")))
                        continue
                    instructions.append((args, operator))
                return pikepdf.unparse_content_stream(instructions)

            original = flatten(page, page.obj.get("/Resources", {}), f"p{page_number}")
            box = tuple(map(float, page.obj.get("/CropBox", page.obj["/MediaBox"])))
            unit = float(page.obj.get("/UserUnit", 1))
            rotation = int(page.obj.get("/Rotate", 0)) % 360
            if request.scale != 1:
                s = request.scale
                x0, y0, x1, y1 = box
                prefix = f"q {s} 0 0 {s} {x0 * (1 - s)} {y0 * (1 - s)} cm\n".encode()
                original = prefix + original + b"\nQ\n"
                box = (x0, y0, x0 + (x1 - x0) * s, y0 + (y1 - y0) * s)
                page.obj["/MediaBox"] = pikepdf.Array(box)
                page.obj["/CropBox"] = pikepdf.Array(box)
            frame = PageFrame(box, unit, rotation)
            overlay = ["q", "0 G", "1 J", "1 j"]
            overlay_points = []

            def draw_path(points, close, width, dashes):
                if len(points) < 2:
                    return
                converted = [frame.to_pdf(p) for p in points]
                overlay_points.extend(converted)
                overlay.append(f"{width / (unit * MM_PER_PT):.6f} w")
                overlay.append(
                    "["
                    + " ".join(f"{d / (unit * MM_PER_PT):.6f}" for d in dashes)
                    + "] 0 d"
                )
                overlay.append(f"{converted[0][0]:.6f} {converted[0][1]:.6f} m")
                overlay.extend(f"{x:.6f} {y:.6f} l" for x, y in converted[1:])
                if close:
                    overlay.append("h")
                overlay.append("S")

            if request.generate:
                for result in analysis.generated:
                    if request.include_sewing:
                        draw_path(result.sewing, True, 0.25, [2, 1.2])
                    if request.include_muslin:
                        draw_path(result.muslin, True, 0.4, [])
                        for mark in result.notches:
                            draw_path(mark, False, 0.3, [])
            overlay.append("Q")
            page.obj["/Contents"] = pdf.make_stream(
                b"q\n" + original + b"\nQ\n" + "\n".join(overlay).encode()
            )
            if overlay_points:
                xs, ys = zip(*overlay_points)
                margin = 1 / (unit * MM_PER_PT)
                expanded = (
                    min(box[0], min(xs) - margin),
                    min(box[1], min(ys) - margin),
                    max(box[2], max(xs) + margin),
                    max(box[3], max(ys) + margin),
                )
                page.obj["/MediaBox"] = pikepdf.Array(expanded)
                page.obj["/CropBox"] = pikepdf.Array(expanded)
        # All original optional groups have been resolved into static paint.
        if "/OCProperties" in pdf.Root:
            del pdf.Root["/OCProperties"]
        pdf.docinfo["/Title"] = "Pattern Studio — " + (request.size or "pattern")
        pdf.docinfo["/Creator"] = "Pattern Studio"
        output = BytesIO()
        pdf.save(output)
        return output.getvalue()
