'''
CRYOSAUR: lamella/volume annotation GUI
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

# -- annotate: launches the lamella annotation GUI for one session
@register('annotate', group='project')
def annotate(
    db_path: Annotated[
        Path,
        typer.Option('--db-path', help='Path to the annotation SQLite database.'),
    ],
    session_id: Annotated[
        str,
        typer.Option('--session-id', help='Session to annotate.'),
    ],
):
    '''
    Launch the lamella annotation GUI for a session.
    '''
    import sys

    session = store.get_session(db_path, session_id)
    if session is None:
        raise CryosaurError(f'No session <cyan>{session_id}</cyan> in <cyan>{db_path}</cyan>')

    # Imported lazily so PySide6/PyVista are only pulled in when annotate actually launches
    from PySide6.QtWidgets import QApplication
    from cryosaur.commands.project.utils.annotate_window import AnnotateWindow

    app = QApplication(sys.argv)
    window = AnnotateWindow(db_path, session)
    window.show()
    log.info(f'Launched annotate for session <cyan>{session_id}</cyan>')
    app.exec()
