'''
CRYOSAUR: extract/render/cache segmentation overlay for lamella
'''

# -- Import external dependencies
import typer
from pathlib import Path
from typing import Annotated

# -- Import cryosaur utilities
from cryosaur.utils.project import store
from cryosaur.utils.cli.options import DbPathOption
from cryosaur.utils.cli.registry import register
from cryosaur.utils.config import load_config, resolve_db_path
from cryosaur.utils.errors import CryosaurError
from cryosaur.utils.log import log

# -- render: extracts a surface mesh from segmentation output for one lamella, caches it, writes a thumbnail, and records an overlay row
@register('render', group='project')
def render(
    session_id: Annotated[
        str,
        typer.Option('--session-id', help='Session the lamella(e) belong to.'),
    ],
    seg_type: Annotated[
        str,
        typer.Option('--seg-type', help="Segmentation source, e.g. 'membrain-seg' or 'easymode'."),
    ],
    lamella_name: Annotated[
        str | None,
        typer.Option('--lamella-name', help='Lamella to render an overlay for (required unless --all).', show_default=False),
    ] = None,
    all_lamellae: Annotated[
        bool,
        typer.Option('--all', help='Render every lamella in the session instead of one.', show_default=False),
    ] = False,
    db_path: DbPathOption = None,
):
    '''
    Extract and cache a segmentation surface overlay for a lamella.
    '''
    from cryosaur.utils.project.overlay import extract_and_cache_overlay

    resolved_db_path = resolve_db_path(load_config(), db_path)

    lamella = _find_lamella(resolved_db_path, lamella_id)
    session = store.get_session(resolved_db_path, lamella.session_id)
    seg_dir = session.paths.get('segmentations')
    if not seg_dir:
        raise CryosaurError(f'Session <cyan>{session.session_id}</cyan> has no <cyan>segmentations</cyan> path set')

    if all_lamellae:
        lamellae = store.list_lamellae(resolved_db_path, session_id)
    elif lamella_name is not None:
        lamella = store.get_lamella_by_name(resolved_db_path, session_id, lamella_name)
        if lamella is None:
            raise CryosaurError(f'No lamella <cyan>{lamella_name}</cyan> in session <cyan>{session_id}</cyan>')
        lamellae = [lamella]
    else:
        raise CryosaurError('Pass --lamella-name or --all')

    for lamella in lamellae:
        mesh_path, thumbnail_path = extract_and_cache_overlay(Path(seg_dir), lamella, seg_type)
        overlay = store.add_overlay(resolved_db_path, lamella.id, seg_type, str(thumbnail_path), mesh_cache_path=str(mesh_path))
        log.info(f'Rendered overlay <cyan>{overlay.id}</cyan> for lamella <cyan>{lamella.lamella_name}</cyan>')