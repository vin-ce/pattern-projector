from typing import Literal
from pydantic import BaseModel, Field

Point = tuple[float, float]


class Layer(BaseModel):
    id: str
    name: str
    kind: Literal["size", "grid", "background", "shared"]
    visible: bool
    dash_mm: list[float] = Field(default_factory=list)


class CalibrationReference(BaseModel):
    label: str
    width_mm: float
    height_mm: float
    expected_mm: float
    error_mm: float
    verified: bool


class PageInfo(BaseModel):
    number: int
    width_mm: float
    height_mm: float
    rotation: int


class PatternDocument(BaseModel):
    id: str
    name: str
    sha256: str
    pages: list[PageInfo]
    layers: list[Layer]
    sizes: list[str]
    calibration: list[CalibrationReference]
    source_allowance_mm: float | None
    source_hem_mm: float | None
    notices: list[str]


class AllowanceSettings(BaseModel):
    seam_mm: float = Field(default=9.525, ge=0, le=100)
    muslin_mm: float = Field(default=25.4, gt=0, le=150)
    hem_mm: float = Field(default=50.8, ge=0, le=150)
    preserve_hem: bool = True


class AnalysisRequest(BaseModel):
    size: str | None = None
    page: int = Field(default=1, ge=1)
    scale: float = Field(default=1, gt=0.05, le=20)
    settings: AllowanceSettings = Field(default_factory=AllowanceSettings)
    generate: bool = False
    confirmed_piece_ids: list[str] = Field(default_factory=list)
    excluded_piece_ids: list[str] = Field(default_factory=list)
    hem_piece_ids: list[str] = Field(default_factory=list)


class Piece(BaseModel):
    id: str
    name: str
    page: int
    size: str | None
    source_path_ids: list[str]
    boundary: list[Point]
    bounds: tuple[float, float, float, float]
    area_mm2: float
    status: Literal["ready", "open", "review", "excluded"]
    is_trouser: bool = False
    fold_edge: bool = False
    hem_location: Literal["bottom", "top"] | None = None
    can_confirm: bool = True
    notices: list[str] = Field(default_factory=list)


class Marking(BaseModel):
    id: str
    path: str
    width_mm: float
    dash_mm: list[float] = Field(default_factory=list)
    fill: bool = False
    stroke: bool = True


class GeneratedPiece(BaseModel):
    piece_id: str
    sewing: list[Point]
    muslin: list[Point]
    notches: list[list[Point]]
    hem_applied: bool


class PatternAnalysis(BaseModel):
    pieces: list[Piece]
    generated: list[GeneratedPiece]
    markings: list[Marking]
    source_paths: list[Marking] = Field(default_factory=list)
    bounds: tuple[float, float, float, float] | None
    notices: list[str]
    curve_tolerance_mm: float = 0.02


class ExportRequest(AnalysisRequest):
    include_original: bool = True
    include_sewing: bool = True
    include_muslin: bool = True
    monochrome: bool = True
    hidden_layer_names: list[str] = Field(default_factory=list)
    allow_partial: bool = False


class SavedWorkspace(BaseModel):
    version: Literal[1] = 1
    document_id: str
    analysis: AnalysisRequest
    hidden_layer_names: list[str] = Field(default_factory=list)
    monochrome: bool = True


class SessionState(BaseModel):
    document: PatternDocument
    workspace: SavedWorkspace | None = None
