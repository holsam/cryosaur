'''
CRYOSAUR: export a session's lamellae, notes, points and screenshots as a single Markdown report
'''

# -- Import external dependencies
import typer
from pathlib import Path
from typing import Annotated

# -- Import cryosaur utilities
from cryosaur.utils.cli.options import DbPathOption, ScreenshotsDirOption
from cryosaur.utils.cli.registry import register
from cryosaur.utils.config import load_config, resolve_db_path, resolve_session_screenshots_root
from cryosaur.utils.errors import CryosaurError
from cryosaur.utils.log import log
from cryosaur.utils.project import store
from cryosaur.utils.project.report import render_report_markdown

# -- export_report: writes <output_dir>/report.md summarising every lamella's status/notes/points/screenshot for session_id
@register('export-report', group='project', rich_help_panel='Data Import/Export')
def export_report(
    session_id: Annotated[str, typer.Option('--session-id', help='Session to export a report for.')],
    output_dir: Annotated[Path | None, typer.Option('--output-dir', help='Directory to write report.md into (defaults to the screenshots root for this session).', show_default=False)] = None,
    db_path: DbPathOption = None,
    screenshots_dir: ScreenshotsDirOption = None,
):
    '''
    Export a Markdown report of every lamella's annotation state and latest screenshot.
    '''
    config = load_config()
    resolved_db_path = resolve_db_path(config, db_path)
    session = store.get_session(resolved_db_path, session_id)
    if session is None:
        raise CryosaurError(f'No session <cyan>{session_id}</cyan> in <cyan>{resolved_db_path}</cyan>')
    resolved_output_dir = output_dir or resolve_session_screenshots_root(config, screenshots_dir, session.session_name)
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    lamellae = store.list_lamellae(resolved_db_path, session_id)
    lamellae_with_annotations = [(lamella, store.get_annotations_for_lamella(resolved_db_path, lamella.id)) for lamella in lamellae]
    report_path = resolved_output_dir / 'report.md'
    report_path.write_text(render_report_markdown(session, lamellae_with_annotations, resolved_output_dir))
    log.info(f'Wrote report to <cyan>{report_path}</cyan>')
