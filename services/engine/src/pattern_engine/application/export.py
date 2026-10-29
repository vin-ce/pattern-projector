from pattern_engine.application.analyze import analyze
from pattern_engine.domain.models import ExportRequest
from pattern_engine.pdf.exporter import write_pdf
from pattern_engine.storage.projects import get_document, original_path


def export_pdf(document_id: str, request: ExportRequest) -> bytes:
    document = get_document(document_id)
    analyses = []
    for page in document.pages:
        result = analyze(document_id, request.model_copy(update={"page": page.number}))
        if (
            request.generate
            and (request.include_sewing or request.include_muslin)
            and not request.allow_partial
        ):
            eligible = [piece for piece in result.pieces if piece.status != "excluded"]
            if len(result.generated) != len(eligible):
                raise ValueError(
                    "Some pieces need review or could not be offset. Confirm partial export, or export the original size only."
                )
        analyses.append(result)
    return write_pdf(original_path(document_id), request, analyses)
