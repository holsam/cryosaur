'''
CRYOSAUR: annotation screenshot capture
'''

# -- Import external dependencies
import tomli_w
from pathlib import Path

# -- Import cryosaur utilities
from cryosaur.utils.project.schema import LamellaRecord, NoteAnnotation, PointAnnotation

# -- SCREENSHOT_FILENAME: define base name for screenshots
SCREENSHOT_FILENAME = 'latest.png'
# -- SIDECAR_FILENAME: define base name for TOML sidecar
SIDECAR_FILENAME = 'latest.toml'

# -- capture_screenshot: returns (screenshot_path, sidecar_path) after overwriting out_dir/latest.png and out_dir/latest.toml with plotter's current view and the lamella's current annotation state
def capture_screenshot(plotter, out_dir: Path, lamella: LamellaRecord, notes: list[NoteAnnotation], points: list[PointAnnotation]) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    screenshot_path = out_dir / SCREENSHOT_FILENAME
    sidecar_path = out_dir / SIDECAR_FILENAME

    plotter.screenshot(str(screenshot_path))

    sidecar = {
        'lamella_name': lamella.lamella_name,
        'status': lamella.status,
        'notes': [n.model_dump() for n in notes],
        'points': [p.model_dump() for p in points],
    }
    sidecar_path.write_bytes(tomli_w.dumps(sidecar).encode('utf-8'))
    return screenshot_path, sidecar_path
