'''
CRYOSAUR: `cryosaur project view` -- shells out to the local-only Streamlit dashboard
'''

# -- Import external dependencies
import subprocess, sys, typer
from pathlib import Path
from typing import Annotated

# -- Import cryosaur utilities
from cryosaur.utils.project import store
from cryosaur.utils.cli.options import DbPathOption
from cryosaur.utils.cli.registry import register
from cryosaur.utils.config import load_config, resolve_db_path
from cryosaur.utils.errors import CryosaurError

# -- _APP_PATH: path to the Streamlit app module, relative to this package
_APP_PATH = Path(__file__).resolve().parent / 'view_app.py'

# -- build_streamlit_args: returns the argv for the `streamlit run` invocation, split out for testing without launching a browser
def build_streamlit_args(db_path: Path) -> list[str]:
    return [sys.executable, '-m', 'streamlit', 'run', str(_APP_PATH), '--', '--db-path', str(db_path)]

# -- view: launches the local-only Streamlit dashboard for db_path
@register('view', group='project')
def view(
    db_path: DbPathOption = None,
):
    '''
    Launch the local-only Streamlit dashboard for the annotation store.
    '''
    resolved_db_path = resolve_db_path(load_config(), db_path)
    store.init_db(resolved_db_path)  # create database if it doesn't exist
    subprocess.run(build_streamlit_args(resolved_db_path))