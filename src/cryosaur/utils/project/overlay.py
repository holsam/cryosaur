'''
CRYOSAUR: segmentation surface extraction and thumbnailing, shared by render and the annotate GUI's cache
'''

# -- Import external dependencies
from pathlib import Path

# -- Import cryosaur utilities
from cryosaur.utils.project.schema import LamellaRecord
from cryosaur.utils.errors import CryosaurError

# -- extract_and_cache_overlay: returns (mesh_cache_path, thumbnail_path) after extracting a surface from seg_dir/<lamella_name>.mrc and writing both to disk next to it
def extract_and_cache_overlay(seg_dir: Path, lamella: LamellaRecord, seg_type: str) -> tuple[Path, Path]:
    import mrcfile, pyvista as pv

    seg_path = seg_dir / f'{lamella.lamella_name}.mrc'
    if not seg_path.exists():
        raise CryosaurError(f'No segmentation volume at <cyan>{seg_path}</cyan>')

    with mrcfile.open(seg_path, permissive=True) as mrc:
        volume = pv.wrap(mrc.data)
    surface = volume.contour()

    cache_dir = seg_dir / '.cryosaur_cache'
    cache_dir.mkdir(exist_ok=True)
    mesh_path = cache_dir / f'{lamella.lamella_name}_{seg_type}.vtp'
    surface.save(mesh_path)

    thumbnail_path = cache_dir / f'{lamella.lamella_name}_{seg_type}.png'
    plotter = pv.Plotter(off_screen=True)
    plotter.add_mesh(surface)
    plotter.screenshot(str(thumbnail_path))
    plotter.close()

    return mesh_path, thumbnail_path
