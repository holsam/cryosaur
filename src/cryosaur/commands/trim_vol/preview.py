'''
CRYOSAUR: preview stitching for the trim-vol command
'''

# -- Import external dependencies
import mrcfile, numpy as np
from pathlib import Path
from PIL import Image, ImageDraw

# -- Define constants for panel label contents and sizes
_PANEL_LABELS = ('Original', 'Filtered', 'Flattened', 'Trimmed')
_LABEL_HEIGHT_PX = 24

# -- extract_xz_slice: returns the XZ plane at the given Y index (default: middle) as a normalised 8-bit array
def extract_xz_slice(mrc_path: Path, y_index: int | None = None) -> np.ndarray:
    with mrcfile.open(mrc_path, permissive=True) as mrc:
        data = mrc.data  # shape (nz, ny, nx)
    y = y_index if y_index is not None else data.shape[1] // 2
    plane = data[:, y, :]
    plane = plane - plane.min()
    if plane.max() > 0:
        plane = (plane / plane.max() * 255)
    return plane.astype(np.uint8)

# -- place_on_canvas: pastes a slice onto a canvas of the original's XZ shape, centred if smaller than original
def place_on_canvas(slice_array: np.ndarray, canvas_shape: tuple[int, int]) -> Image.Image:
    canvas = Image.new('L', (canvas_shape[1], canvas_shape[0]), color=0)
    panel = Image.fromarray(slice_array)
    offset_x = (canvas_shape[1] - panel.width) // 2
    offset_z = (canvas_shape[0] - panel.height) // 2
    canvas.paste(panel, (offset_x, offset_z))
    return canvas

# -- build_preview: stitches the four labelled stages into one vertical composite image
def build_preview(stage_paths: dict[str, Path], output_path: Path) -> Path:
    with mrcfile.open(stage_paths['Original'], permissive=True) as mrc:
        canvas_shape = (mrc.data.shape[0], mrc.data.shape[2])  # (nz, nx)

    panels = []
    for label in _PANEL_LABELS:
        slice_array = extract_xz_slice(stage_paths[label])
        panel = place_on_canvas(slice_array, canvas_shape)
        labelled = Image.new('L', (panel.width, panel.height + _LABEL_HEIGHT_PX), color=255)
        labelled.paste(panel, (0, _LABEL_HEIGHT_PX))
        ImageDraw.Draw(labelled).text((4, 4), label, fill=0)
        panels.append(labelled)

    total_height = sum(p.height for p in panels)
    composite = Image.new('L', (canvas_shape[1], total_height), color=255)
    y = 0
    for panel in panels:
        composite.paste(panel, (0, y))
        y += panel.height

    composite.save(output_path)
    return output_path