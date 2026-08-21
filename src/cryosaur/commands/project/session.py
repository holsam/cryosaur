'''
CRYOSAUR: create/list/show/delete sessions without the dashboard
'''

# -- Import external dependencies
import typer, uuid
from typing import Annotated
from rich.console import Console
from rich.table import Table

# -- Import cryosaur utilities
from cryosaur.utils.cli.options import DbPathOption
from cryosaur.utils.cli.registry import register
from cryosaur.utils.config import load_config, resolve_db_path
from cryosaur.utils.errors import CryosaurError
from cryosaur.utils.log import log
from cryosaur.utils.project import store

# -- _parse_paths: returns a dict from repeated 'key=value' strings
def _parse_paths(entries: list[str]) -> dict[str, str]:
    paths = {}
    for entry in entries:
        if '=' not in entry:
            raise CryosaurError(f'--path {entry!r} must be key=value')
        key, _, value = entry.partition('=')
        paths[key] = value
    return paths

# -- session_create: creates a new session, optionally seeded with paths
@register('create', group='session')
def session_create(
    name: Annotated[str, typer.Option('--name', help='Session name.')],
    path: Annotated[
        list[str],
        typer.Option('--path', help='A session path as key=value, e.g. --path raw=/data/raw. Repeatable.'),
    ] = [],
    db_path: DbPathOption = None,
):
    '''
    Create a new annotation session.
    '''
    resolved_db_path = resolve_db_path(load_config(), db_path)
    store.init_db(resolved_db_path)

    session_id = uuid.uuid4().hex[:12]
    store.add_session(resolved_db_path, session_id, name, _parse_paths(path))
    log.info(f'Created session <cyan>{session_id}</cyan> ({name!r})')

# -- session_list: lists every session
@register('list', group='session')
def session_list(db_path: DbPathOption = None):
    '''
    List every session in the annotation store.
    '''
    resolved_db_path = resolve_db_path(load_config(), db_path)
    store.init_db(resolved_db_path)

    table = Table('session_id', 'name', 'lamellae', 'created_at')
    for session in store.list_sessions(resolved_db_path):
        lamella_count = len(store.list_lamellae(resolved_db_path, session.session_id))
        table.add_row(session.session_id, session.session_name, str(lamella_count), session.created_at)
    Console().print(table)

# -- session_show: prints one session's paths and lamellae
@register('show', group='session')
def session_show(
    session_id: Annotated[str, typer.Argument(help='Session to show.')],
    db_path: DbPathOption = None,
):
    '''
    Show a session's paths and lamellae.
    '''
    resolved_db_path = resolve_db_path(load_config(), db_path)
    session = store.get_session(resolved_db_path, session_id)
    if session is None:
        raise CryosaurError(f'No session <cyan>{session_id}</cyan>')

    console = Console()
    console.print(f'[bold]{session.session_name}[/] ({session.session_id})')
    console.print(f'paths: {session.paths}')

    table = Table('id', 'name', 'milling_order', 'status')
    for lamella in store.list_lamellae(resolved_db_path, session_id):
        table.add_row(str(lamella.id), lamella.lamella_name, str(lamella.milling_order), lamella.status or '')
    console.print(table)

# -- session_delete: deletes a session and everything under it, after confirmation
@register('delete', group='session')
def session_delete(
    session_id: Annotated[str, typer.Argument(help='Session to delete.')],
    yes: Annotated[bool, typer.Option('--yes', help='Skip the confirmation prompt.', show_default=False)] = False,
    db_path: DbPathOption = None,
):
    '''
    Delete a session and every lamella/note/point/overlay under it.
    '''
    resolved_db_path = resolve_db_path(load_config(), db_path)
    session = store.get_session(resolved_db_path, session_id)
    if session is None:
        raise CryosaurError(f'No session <cyan>{session_id}</cyan>')

    if not yes:
        answer = log.input(f'Delete session {session.session_name!r} and everything in it?', choices=['y', 'n'], default='n')
        if answer != 'y':
            log.info('Aborted')
            return

    store.delete_session(resolved_db_path, session_id)
