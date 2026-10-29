from pathlib import Path
from typing import Annotated
import os
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from starlette.concurrency import run_in_threadpool
from pattern_engine.application.analyze import analyze
from pattern_engine.domain.models import (
    AnalysisRequest,
    ExportRequest,
    PatternAnalysis,
    PatternDocument,
    SavedWorkspace,
    SessionState,
)
from pattern_engine.application.export import export_pdf
from pattern_engine.storage.projects import (
    get_document,
    import_document,
    original_path,
    save_workspace,
    session,
)

app = FastAPI(
    title="Pattern Studio Engine",
    version="0.1.0",
    description="Local PDF sewing-pattern processing in physical millimetres.",
)


@app.exception_handler(ValueError)
async def invalid_request(_, error):
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=422, content={"detail": str(error)})


@app.exception_handler(FileNotFoundError)
async def missing_project(_, error):
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=404, content={"detail": str(error)})


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "engine": "Clipper2", "units": "mm"}


@app.post("/api/documents", response_model=PatternDocument)
async def upload(file: Annotated[UploadFile, File()]):
    content = await file.read(40 * 1024 * 1024 + 1)
    if len(content) > 40 * 1024 * 1024:
        raise HTTPException(413, "PDFs up to 40 MB are supported.")
    if not content.startswith(b"%PDF-"):
        raise HTTPException(422, "Choose a valid PDF file.")
    try:
        return await run_in_threadpool(
            import_document, file.filename or "Pattern.pdf", content
        )
    except ValueError:
        raise
    except Exception as error:
        raise HTTPException(
            422,
            "This PDF could not be read. Encrypted or unsupported PDFs need to be unlocked or converted first.",
        ) from error


@app.post("/api/example", response_model=PatternDocument)
def example():
    path = os.environ.get("PATTERN_STUDIO_EXAMPLE")
    if not path or not Path(path).is_file():
        raise HTTPException(404, "No local example configured. Open a PDF to begin.")
    return import_document(Path(path).name, Path(path).read_bytes())


@app.get("/api/documents/{document_id}", response_model=SessionState)
def read_session(document_id: str):
    return session(document_id)


@app.get("/api/documents/{document_id}/original")
def original(document_id: str):
    return FileResponse(original_path(document_id), media_type="application/pdf")


@app.post("/api/documents/{document_id}/analysis", response_model=PatternAnalysis)
def inspect(document_id: str, request: AnalysisRequest):
    return analyze(document_id, request)


@app.put("/api/documents/{document_id}/workspace", response_model=SavedWorkspace)
def persist(document_id: str, workspace: SavedWorkspace):
    save_workspace(document_id, workspace)
    return workspace


@app.post("/api/documents/{document_id}/export")
def export(document_id: str, request: ExportRequest):
    name = Path(get_document(document_id).name).stem
    # Keep Content-Disposition ASCII-safe. The browser supplies the display name.
    return Response(
        export_pdf(document_id, request),
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="pattern-studio.pdf"',
            "X-Pattern-Source": name.encode("ascii", "ignore").decode()[:120],
        },
    )
