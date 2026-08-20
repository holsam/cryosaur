'''
CRYOSAUR: extract/render/cache segmentation overlay for lamella
'''

# -- Import external dependencies
import typer
from pathlib import Path
from typing import Annotated

# -- Import cryosaur utilities
from cryosaur.utils.project import store
from cryosaur.utils.cli.registry import register
from cryosaur.utils.errors import CryosaurError
from cryosaur.utils.log import log

# -- render: extracts a surface mesh from segmentation output for one lamella, caches it, writes a thumbnail, and records an overlay row
@register('render', group='project')
def render(
    db_path: Annotated[
        Path,
        typer.Option('--db-path', help='Path to the annotation SQLite database.'),
    ],
    lamella_id: Annotated[
        int,
        typer.Option('--lamella-id', help='Lamella to render an overlay for.'),
    ],
    seg_type: Annotated[
        str,
        typer.Option('--seg-type', help="Segmentation source, e.g. 'membrain-seg' or 'easymode'."),
    ],
):
    '''
    Extract and cache a segmentation surface overlay for a lamella.
    '''
    from cryosaur.commands.project.utils.overlay import extract_and_cache_overlay

    lamella = _find_lamella(db_path, lamella_id)
    session = store.get_session(db_path, lamella.session_id)
    seg_dir = session.paths.get('segmentations')
    if not seg_dir:
        raise CryosaurError(f'Session <cyan>{session.session_id}</cyan> has no <cyan>segmentations</cyan> path set')

    mesh_path, thumbnail_path = extract_and_cache_overlay(Path(seg_dir), lamella, seg_type)
    overlay = store.add_overlay(db_path, lamella_id, seg_type, str(thumbnail_path), mesh_cache_path=str(mesh_path))
    log.info(f'Rendered overlay <cyan>{overlay.id}</cyan> for lamella <cyan>{lamella.lamella_name}</cyan>')

# -- _find_lamella: returns the LamellaRecord for lamella_id, raising CryosaurError if it doesn't exist in db_path
def _find_lamella(db_path: Path, lamella_id: int):
    for session in store.list_sessions(db_path):
        for lamella in store.list_lamellae(db_path, session.session_id):
            if lamella.id == lamella_id:
                return lamella
    raise CryosaurError(f'No lamella with id <cyan>{lamella_id}</cyan> in <cyan>{db_path}</cyan>')
