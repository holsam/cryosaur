'''
CRYOSAUR: command line TOML import with diff confirmation
'''

# -- Import external dependencies
import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table
from typing import Annotated

# -- Import cryosaur utilities
from cryosaur.utils.cli.options import DbPathOption
from cryosaur.utils.cli.registry import register
from cryosaur.utils.config import load_config, resolve_db_path
from cryosaur.utils.log import log
from cryosaur.utils.project import store, toml_io

# -- _print_plan: prints a diff table for every conflicting session/lamella in plan
def _print_plan(plan: toml_io.ImportPlan) -> None:
    console = Console()
    if plan.conflicting_sessions:
        table = Table('session_id', 'existing name', 'incoming name', 'existing paths', 'incoming paths', title='Conflicting sessions')
        for diff in plan.conflicting_sessions:
            table.add_row(diff.session_id, diff.existing_name, diff.incoming_name, str(diff.existing_paths), str(diff.incoming_paths))
        console.print(table)
    if plan.conflicting_lamellae:
        table = Table('lamella', 'existing status', 'incoming status', 'existing notes/points/overlays', 'incoming notes/points/overlays', title='Conflicting lamellae')
        for diff in plan.conflicting_lamellae:
            table.add_row(
                diff.lamella_name, diff.existing_status or '', diff.incoming_status or '',
                f'{diff.existing_notes}/{diff.existing_points}/{diff.existing_overlays}',
                f'{diff.incoming_notes}/{diff.incoming_points}/{diff.incoming_overlays}',
            )
        console.print(table)
    console.print(f'{len(plan.new_sessions)} new session(s), {len(plan.new_lamellae)} new lamella/lamellae (no conflict)')

# -- import_toml_command: plans a TOML import, shows conflicts, confirms skip/replace, then applies
@register('import-toml', group='project', rich_help_panel='Data Import/Export')
def import_toml_command(
    path: Annotated[Path, typer.Argument(help='TOML file to import.', exists=True)],
    on_conflict: Annotated[
        str | None,
        typer.Option('--on-conflict', help="Skip the prompt and always 'skip' or 'replace' conflicting sessions/lamellae.", show_default=False),
    ] = None,
    db_path: DbPathOption = None,
):
    '''
    Import a TOML export, diffing and confirming conflicts before writing anything.
    '''
    resolved_db_path = resolve_db_path(load_config(), db_path)
    store.init_db(resolved_db_path)

    plan = toml_io.plan_import(resolved_db_path, path)
    resolved_on_conflict = on_conflict
    if plan.has_conflicts and resolved_on_conflict is None:
        _print_plan(plan)
        resolved_on_conflict = log.input('Skip or replace conflicting sessions/lamellae?', choices=['skip', 'replace'], default='skip')
    resolved_on_conflict = resolved_on_conflict or 'skip'

    summary = toml_io.apply_import(resolved_db_path, plan, resolved_on_conflict)
    log.info(f'Created {summary.sessions_created} session(s)/{summary.lamellae_created} lamella(e); {summary.sessions_skipped + summary.lamellae_skipped} skipped; {summary.sessions_replaced + summary.lamellae_replaced} replaced')