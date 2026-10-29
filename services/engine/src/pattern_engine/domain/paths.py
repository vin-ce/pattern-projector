from dataclasses import dataclass, field
from pattern_engine.domain.models import Point


@dataclass
class Drawing:
    """Source path geometry and provenance, independent of its file format."""

    id: str
    page: int
    layer: str | None
    layer_id: str | None
    commands: list
    subpaths: list[list[Point]]
    closed: list[bool]
    stroke: bool
    width_mm: float
    dash_mm: list[float] = field(default_factory=list)
    fill: bool = False

    @property
    def svg(self):
        return " ".join(
            cmd[0] + " " + " ".join(f"{n:.5f}" for p in cmd[1:] for n in p)
            for cmd in self.commands
        )
