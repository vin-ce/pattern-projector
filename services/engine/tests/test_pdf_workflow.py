from hashlib import sha256
from io import BytesIO
import pikepdf
import pytest
from fastapi.testclient import TestClient
from pattern_engine.api.main import app
from pattern_engine.domain.models import AnalysisRequest, ExportRequest, SavedWorkspace
from pattern_engine.pdf.reader import read_pdf
from pattern_engine.application.export import export_pdf
from pattern_engine.application.analyze import analyze
from pattern_engine.storage import projects


def pattern_bytes():
    pdf = pikepdf.Pdf.new()
    page = pdf.add_blank_page(page_size=(1000, 1000))
    groups = {
        name: pdf.make_indirect(
            pikepdf.Dictionary(Type=pikepdf.Name("/OCG"), Name=name)
        )
        for name in ("M", "S", "Titles", "Calibration squares")
    }
    pdf.Root["/OCProperties"] = pikepdf.Dictionary(
        OCGs=pikepdf.Array(groups.values()),
        D=pikepdf.Dictionary(
            Order=pikepdf.Array(groups.values()), ON=pikepdf.Array(groups.values())
        ),
    )
    page.obj["/Resources"] = pikepdf.Dictionary(
        Properties=pikepdf.Dictionary(
            {f"/{name.replace(' ', '')}": group for name, group in groups.items()}
        )
    )
    page.obj["/Contents"] = pdf.make_stream(b"""q
    /OC /S BDC 1 0 0 RG 3 w 500 300 200 400 re S 1 0 0 1 5 0 cm EMC
    /OC /M BDC 0 0 0 RG 1 w 100 300 200 400 re S 100 500 m 115 500 l S EMC
    /OC /Titles BDC 190 400 m 190 650 l S EMC
    /OC /Calibrationsquares BDC 50 50 144 144 re S 250 50 141.732 141.732 re S EMC
    Q""")
    result = BytesIO()
    pdf.save(result)
    return result.getvalue()


@pytest.fixture
def local_store(tmp_path, monkeypatch):
    monkeypatch.setattr(projects, "ROOT", tmp_path)
    projects.parsed.cache_clear()
    yield tmp_path
    projects.parsed.cache_clear()


def test_upload_select_export_preserves_source_and_references(local_store, tmp_path):
    original = pattern_bytes()
    document = projects.import_document("fixture.pdf", original)
    parsed = projects.parsed(document.id)
    assert len(parsed.calibration) == 2 and all(c.verified for c in parsed.calibration)
    selected = analyze(document.id, AnalysisRequest(size="M"))
    assert len(selected.pieces) == 1
    result = export_pdf(document.id, ExportRequest(size="M", generate=False))
    output = tmp_path / "selected.pdf"
    output.write_bytes(result)
    reopened = read_pdf(output)
    assert len([d for d in reopened.drawings if d.stroke]) == 5
    assert min(x for x, y in reopened.drawings[0].subpaths[0]) == pytest.approx(
        105 * 25.4 / 72, abs=1e-6
    )
    assert projects.original_path(document.id).read_bytes() == original
    assert document.sha256 == sha256(original).hexdigest()
    with pikepdf.open(output) as pdf:
        assert "/OCProperties" not in pdf.Root
    assert all(
        min(x for path in d.subpaths for x, y in path) < 160 for d in reopened.drawings
    )


def test_generated_pdf_has_measured_vector_offsets(local_store, tmp_path):
    document = projects.import_document("fixture.pdf", pattern_bytes())
    request = ExportRequest(size="M", generate=True, settings={"preserve_hem": False})
    result = export_pdf(document.id, request)
    output = tmp_path / "muslin.pdf"
    output.write_bytes(result)
    reopened = read_pdf(output)
    generated = [d for d in reopened.drawings if d.stroke and len(d.subpaths[0]) > 3]
    assert len(generated) == 5
    xs = [x for x, y in generated[-1].subpaths[0]]
    assert max(xs) - min(xs) == pytest.approx(200 * 25.4 / 72 + 2 * 15.875, abs=0.0001)


def test_api_rejects_invalid_input_and_restores_workspace(local_store):
    with TestClient(app) as client:
        bad = client.post(
            "/api/documents",
            files={"file": ("bad.pdf", b"not a pdf", "application/pdf")},
        )
        assert bad.status_code == 422
        document = client.post(
            "/api/documents",
            files={"file": ("fixture.pdf", pattern_bytes(), "application/pdf")},
        ).json()
        id = document["id"]
        assert (
            client.post(
                f"/api/documents/{id}/analysis", json={"size": "XXL"}
            ).status_code
            == 422
        )
        assert (
            client.post(
                f"/api/documents/{id}/analysis", json={"size": "M", "scale": 0}
            ).status_code
            == 422
        )
        workspace = SavedWorkspace(
            document_id=id, analysis=AnalysisRequest(size="M", generate=True)
        )
        assert (
            client.put(
                f"/api/documents/{id}/workspace", json=workspace.model_dump()
            ).status_code
            == 200
        )
        restored = client.get(f"/api/documents/{id}").json()
        assert restored["workspace"]["analysis"]["size"] == "M"
        assert restored["workspace"]["analysis"]["generate"] is True


def test_partial_offsets_require_explicit_export_acknowledgement(local_store):
    document = projects.import_document("fixture.pdf", pattern_bytes())
    request = ExportRequest(
        size="M", generate=True, settings={"seam_mm": 100, "preserve_hem": False}
    )
    with pytest.raises(ValueError, match="Confirm partial export"):
        export_pdf(document.id, request)


def test_new_allowance_expands_page_instead_of_clipping(local_store, tmp_path):
    raw = pattern_bytes()
    with pikepdf.open(BytesIO(raw)) as pdf:
        stream = pdf.pages[0].obj["/Contents"]
        stream.write(
            stream.read_bytes().replace(b"100 300 200 400 re", b"0 300 200 400 re")
        )
        source = BytesIO()
        pdf.save(source)
    document = projects.import_document("edge.pdf", source.getvalue())
    output = export_pdf(
        document.id,
        ExportRequest(size="M", generate=True, settings={"preserve_hem": False}),
    )
    with pikepdf.open(BytesIO(output)) as pdf:
        # Includes the 5-point transform in the excluded size layer and a 1-mm
        # margin around the new cutting boundary.
        assert float(pdf.pages[0].obj["/CropBox"][0]) == pytest.approx(
            5 - (15.875 + 1) * 72 / 25.4, abs=1e-5
        )


def test_filled_size_markings_survive_line_filtering(local_store, tmp_path):
    with pikepdf.open(BytesIO(pattern_bytes())) as pdf:
        stream = pdf.pages[0].obj["/Contents"]
        stream.write(
            stream.read_bytes() + b" /OC /M BDC 150 500 m 155 510 l 145 510 l h f EMC"
        )
        source = BytesIO()
        pdf.save(source)
    document = projects.import_document("filled-mark.pdf", source.getvalue())
    result = analyze(document.id, AnalysisRequest(size="M"))
    assert any(mark.fill and not mark.stroke for mark in result.markings)
    output = tmp_path / "filled.pdf"
    output.write_bytes(
        export_pdf(
            document.id, ExportRequest(size="M", include_original=False, generate=False)
        )
    )
    assert any(d.fill and not d.stroke for d in read_pdf(output).drawings)
