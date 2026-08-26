'''
CRYOSAUR: register a directory of screenshot+sidecar pairs into the annotation store
'''

# -- Import external dependencies
import tomllib, typer
from pathlib import Path
from typing import Annotated

# -- Import cryosaur utilities
from cryosaur.utils.cli.options import DbPathOption
from cryosaur.utils.cli.registry import register
from cryosaur.utils.config import load_config, resolve_db_path
from cryosaur.utils.errors import CryosaurError
from cryosaur.utils.log import log
from cryosaur.utils.project import store

# -- Define image extensions
_IMAGE_EXTS = ('.png', '.jpg', '.jpeg')

# -- ingest_screenshots: registers every screenshot+TOML-sidecar pair (matched by filename stem) in directory as a ScreenshotRecord, matching lamellae by name within session_id
@register('ingest-screenshots', group='project', panel='Data Import/Export')
def ingest_screenshots(
    directory: Annotated[Path, typer.Argument(help='Directory containing screenshot + TOML sidecar pairs.', exists=True, file_okay=False)],
    session_id: Annotated[str, typer.Option('--session-id', help='Session the screenshots belong to.')],
    db_path: DbPathOption = None,
):
    '''
    Register a directory of screenshot+sidecar pairs into the store, so they show up in the gallery.
    '''
    resolved_db_path = resolve_db_path(load_config(), db_path)
    store.init_db(resolved_db_path)
    if store.get_session(resolved_db_path, session_id) is None:
        raise CryosaurError(f'No session <cyan>{session_id}</cyan> in <cyan>{resolved_db_path}</cyan>')
    registered = skipped = 0
    for sidecar_path in sorted(directory.glob('*.toml')):
        with sidecar_path.open('rb') as f:
            sidecar = tomllib.load(f)
        lamella_name = sidecar.get('lamella_name')
        if not lamella_name:
            log.warning(f'{sidecar_path}: no lamella_name key, skipping')
            skipped += 1
            continue
        image_path = next((p for ext in _IMAGE_EXTS if (p := sidecar_path.with_suffix(ext)).exists()), None)
        if image_path is None:
            log.warning(f'{sidecar_path}: no matching image ({sidecar_path.stem}.png/.jpg/.jpeg), skipping')
            skipped += 1
            continue
        lamella = store.get_lamella_by_name(resolved_db_path, session_id, lamella_name)
        if lamella is None:
            log.warning(f'{sidecar_path}: no lamella <cyan>{lamella_name}</cyan> in session <cyan>{session_id}</cyan>, skipping')
            skipped += 1
            continue
        store.add_screenshot(resolved_db_path, lamella.id, str(image_path), str(sidecar_path))
        registered += 1
    log.info(f'Registered {registered} screenshot(s), skipped {skipped}')
