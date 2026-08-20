'''
CRYOSAUR: lamella/volume annotation GUI
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

# -- annotate: launches the lamella annotation GUI for one session
@register('annotate', group='project')
def annotate(
    session_id: Annotated[
        str,
        typer.Option('--session-id', help='Session to annotate.'),
    ],
    db_path: DbPathOption = None,
):
    '''
    Launch the lamella annotation GUI for a session.
    '''
    import sys

    resolved_db_path = resolve_db_path(load_config(), db_path)
    store.init_db(resolved_db_path) # create database if doesn't exist

    session = store.get_session(resolved_db_path, session_id)
    if session is None:
        raise CryosaurError(f'No session <cyan>{session_id}</cyan> in <cyan>{resolved_db_path}</cyan>')

    # Imported lazily so PySide6/PyVista are only pulled in when annotate actually launches
    from PySide6.QtWidgets import QApplication
    from cryosaur.commands.project.utils.annotate_window import AnnotateWindow

    app = QApplication(sys.argv)
    window = AnnotateWindow(resolved_db_path, session)
    window.show()
    log.info(f'Launched annotate for session <cyan>{session_id}</cyan>')
    app.exec()
