'''
CRYOSAUR: `cryosaur project view` -- shells out to the local-only Streamlit dashboard
'''

# -- Import external dependencies
import subprocess, sys, typer
from pathlib import Path
from typing import Annotated

# -- Import cryosaur utilities
from cryosaur.utils.cli.registry import register
from cryosaur.utils.errors import CryosaurError

# -- _APP_PATH: path to the Streamlit app module, relative to this package
_APP_PATH = Path(__file__).resolve().parent / 'view_app.py'

# -- build_streamlit_args: returns the argv for the `streamlit run` invocation, split out for testing without launching a browser
def build_streamlit_args(db_path: Path) -> list[str]:
    return [sys.executable, '-m', 'streamlit', 'run', str(_APP_PATH), '--', '--db-path', str(db_path)]

# -- view: launches the local-only Streamlit dashboard for db_path
@register('view', group='project')
def view(
    db_path: Annotated[
        Path,
        typer.Option('--db-path', help='Path to the annotation SQLite database.'),
    ],
):
    '''
    Launch the local-only Streamlit dashboard for the annotation store.
    '''
    if not db_path.exists():
        raise CryosaurError(f'No annotation database at <cyan>{db_path}</cyan>')
    subprocess.run(build_streamlit_args(db_path))
