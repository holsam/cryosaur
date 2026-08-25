'''
CRYOSAUR: Pydantic models for the annotation store
'''

# -- Import external dependencies
from datetime import datetime, timezone
from pydantic import BaseModel, Field

# -- _now: returns an ISO-8601 UTC timestamp string
def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

# -- SessionRecord: a named annotation session and its resolved paths
class SessionRecord(BaseModel):
    session_id: str
    session_name: str
    paths: dict[str, str] = Field(default_factory=dict)
    created_at: str = Field(default_factory=_now)
    updated_at: str = Field(default_factory=_now)

# -- LamellaRecord: a lamella belonging to exactly one session
class LamellaRecord(BaseModel):
    id: int | None = None
    lamella_name: str
    session_id: str
    grid_name: str | None = None
    milling_order: int | None = None
    status: str | None = None
    created_at: str = Field(default_factory=_now)
    updated_at: str = Field(default_factory=_now)

# -- NoteAnnotation: a free-text note attached to a lamella
class NoteAnnotation(BaseModel):
    id: int | None = None
    lamella_id: int
    text: str
    created_at: str = Field(default_factory=_now)

# -- PointAnnotation: a 3D point placed on a lamella, optionally linked to a note
class PointAnnotation(BaseModel):
    id: int | None = None
    lamella_id: int
    x: float
    y: float
    z: float
    label: str | None = None
    note_id: int | None = None
    created_at: str = Field(default_factory=_now)

# -- OverlayRecord: a cached segmentation overlay for a lamella
class OverlayRecord(BaseModel):
    id: int | None = None
    lamella_id: int
    seg_type: str
    thumbnail_path: str
    mesh_cache_path: str | None = None
    created_at: str = Field(default_factory=_now)

# -- ScreenshotRecord: the latest auto-captured screenshot + annotation-state sidecar for a lamella (one per lamella, overwritten in place)
class ScreenshotRecord(BaseModel):
    id: int | None = None
    lamella_id: int
    path: str
    sidecar_path: str
    created_at: str = Field(default_factory=_now)
