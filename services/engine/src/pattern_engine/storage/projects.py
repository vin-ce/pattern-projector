from functools import lru_cache
from hashlib import sha256
import os
from pathlib import Path
from uuid import UUID, uuid4
from pattern_engine.domain.models import PatternDocument, SavedWorkspace, SessionState
from pattern_engine.pdf.reader import read_pdf

ROOT = Path(
    os.environ.get(
        "PATTERN_STUDIO_DATA", Path(__file__).resolve().parents[5] / ".runtime"
    )
)


def project_dir(document_id: str) -> Path:
    UUID(document_id)
    directory = ROOT / "projects" / document_id
    if not (directory / "original.pdf").is_file():
        raise FileNotFoundError("Pattern not found. Open the PDF again.")
    return directory


def original_path(document_id: str) -> Path:
    return project_dir(document_id) / "original.pdf"


@lru_cache(maxsize=8)
def parsed(document_id: str):
    return read_pdf(original_path(document_id))


def import_document(name: str, content: bytes) -> PatternDocument:
    document_id = str(uuid4())
    directory = ROOT / "projects" / document_id
    directory.mkdir(parents=True)
    (directory / "original.pdf").write_bytes(content)
    try:
        pdf = parsed(document_id)
        sizes = list(
            dict.fromkeys(layer.name for layer in pdf.layers if layer.kind == "size")
        )
        document = PatternDocument(
            id=document_id,
            name=Path(name).name,
            sha256=sha256(content).hexdigest(),
            pages=pdf.pages,
            layers=pdf.layers,
            sizes=sizes,
            calibration=pdf.calibration,
            source_allowance_mm=pdf.seam_mm,
            source_hem_mm=pdf.hem_mm,
            notices=pdf.notices,
        )
        (directory / "document.json").write_text(document.model_dump_json(indent=2))
        return document
    except Exception:
        parsed.cache_clear()
        for file in directory.iterdir():
            file.unlink()
        directory.rmdir()
        raise


def get_document(document_id: str) -> PatternDocument:
    document = PatternDocument.model_validate_json(
        (project_dir(document_id) / "document.json").read_text()
    )
    document.layers = parsed(document_id).layers
    return document


def save_workspace(document_id: str, workspace: SavedWorkspace):
    if workspace.document_id != document_id:
        raise ValueError("Workspace belongs to another pattern.")
    directory = project_dir(document_id)
    temporary = directory / "workspace.tmp"
    temporary.write_text(workspace.model_dump_json(indent=2))
    temporary.replace(directory / "workspace.json")


def session(document_id: str) -> SessionState:
    directory = project_dir(document_id)
    state_path = directory / "workspace.json"
    return SessionState(
        document=get_document(document_id),
        workspace=SavedWorkspace.model_validate_json(state_path.read_text())
        if state_path.exists()
        else None,
    )
