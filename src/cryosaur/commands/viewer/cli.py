'''
CRYOSAUR: viewer command CLI wiring
'''

# -- Import external dependencies
import sys, typer
from pathlib import Path
from typing import Annotated

# -- Import cryosaur utilities
from cryosaur.utils.cli.registry import register
from cryosaur.utils.errors import CryosaurError
from cryosaur.utils.io import _find_files_by_extension
from cryosaur.utils.log import log

# -- gui_view: launches the viewer for a project directory of MRC files
@register('viewer')
def viewer(
    project_dir: Annotated[
        Path,
        typer.Argument(help='Directory containing tomogram MRC files to view.'),
    ],
):
    '''
    Launch the cryosaur viewer for a project directory.
    '''
    if not _find_files_by_extension(project_dir, 'mrc'):
        raise CryosaurError(f'No <cyan>.mrc</cyan> files found in <cyan>{project_dir}</cyan>')

    # Imported lazily so PySide6/VTK are only pulled in when the viewer actually launches
    from PySide6.QtWidgets import QApplication
    from cryosaur.commands.viewer.utils.main_window import MainWindow

    app = QApplication(sys.argv)
    window = MainWindow(project_dir)
    window.show()
    log.info(f'Launched viewer for <cyan>{project_dir}</cyan>')
    app.exec()