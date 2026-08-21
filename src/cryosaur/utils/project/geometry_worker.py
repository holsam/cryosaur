'''
CRYOSAUR: background worker that loads (or builds and caches) a lamella's surface mesh off the UI thread
'''

# -- Import external dependencies
from pathlib import Path
from PySide6.QtCore import QRunnable, Signal

# -- Import cryosaur utilities
from cryosaur.utils.project import store
from cryosaur.utils.project.schema import LamellaRecord
from cryosaur.utils.log import log

# -- GeometryWorker: QRunnable that resolves a lamella's cached mesh (or its most recent overlay) and emits it back to the main thread
class GeometryWorker(QRunnable):
    def __init__(self, db_path: Path, lamella: LamellaRecord, geometry_ready: Signal):
        super().__init__()
        self.db_path = db_path
        self.lamella = lamella
        self.geometry_ready = geometry_ready

    def run(self) -> None:
        import pyvista as pv

        annotations = store.get_annotations_for_lamella(self.db_path, self.lamella.id)
        overlays = [o for o in annotations['overlays'] if o.mesh_cache_path]
        if not overlays:
            log.warning(f'No cached mesh for lamella <cyan>{self.lamella.lamella_name}</cyan>; run `cryosaur project render` first')
            return
        # Reuse most recently generated overlay's cached mesh
        mesh = pv.read(overlays[-1].mesh_cache_path)
        self.geometry_ready.emit(mesh)
