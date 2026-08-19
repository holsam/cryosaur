'''
CRYOSAUR: pydantic models for the tomogram/collection viewer
'''

# -- Import external dependencies
from pathlib import Path
from pydantic import BaseModel, Field

# -- Annotation: a single labelled point placed in a tomogram's volume
class Annotation(BaseModel):
    id: str
    position: tuple[float, float, float]  # voxel coords in the unbinned volume
    label: str
    note: str = ''

# -- TomogramAnnotations: every annotation for one tomogram, persisted as a TOML sidecar next to the .mrc
class TomogramAnnotations(BaseModel):
    tomogram_path: Path
    annotations: list[Annotation] = Field(default_factory=list)

# -- Collection: a group of related tomograms into an ordered 3D stack
class Collection(BaseModel):
    name: str
    members: list[Path] = Field(default_factory=list)
    stack_order: list[Path] = Field(default_factory=list)
