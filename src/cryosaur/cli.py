'''
CRYOSAUR: main CLI entrypoint
'''

# -- Import external dependencies
import typer
from pathlib import Path
from typing import Annotated, Literal

# -- Import cryosaur utilities
from cryosaur.utils.log import configure_logging, log

# -- Initialise Typer class for cryosaur CLI
cryosaur = typer.Typer(
    add_completion=False,
    rich_markup_mode='rich',
    no_args_is_help=True,
    help='🦖 Resources and scripts for investigating ultrastructure using [italic]in situ[/] cryoEM'
)

# -- Create callback to provide logging options and configure logging
@cryosaur.callback()
def logging_callback(
    log_dir: Annotated[
        Path | None,
        typer.Option('-d', '--directory', help='Directory to write log file to.', show_default=None, rich_help_panel='Logging Options')
    ] = None,
    log_mode: Annotated[
        Literal['append', 'new', 'overwrite'],
        typer.Option('-m', '--mode', help='Mode to use for resolving log file.', rich_help_panel='Logging Options')
    ] = 'append',
    quiet: Annotated[
        bool,
        typer.Option('-q', '--quiet', help='Disable all logging except errors.', show_default=False, rich_help_panel='Logging Options')
    ] = False,
    verbosity: Annotated[
        int,
        typer.Option('-v', '--verbose', count=True, help='Increase verbosity of logging.', show_default=False, rich_help_panel='Logging Options', metavar='')
    ] = 0,
):
    # Check quiet and verbose haven't been supplied together
    if quiet and verbosity:
        raise typer.BadParameter('-q/--quiet and -v/--verbose are mutually exclusive.')
    # Clamp verbosity to 3
    verbosity = 3 if verbosity > 3 else verbosity
    # Configure logging
    log_path = configure_logging(directory=log_dir, mode=log_mode, quiet=quiet, verbosity=verbosity)
    # Output confirmation message that logging has been set up
    log.info(f'Log messages will be {"appended" if log_mode == 'append' else "written"} to <cyan>{log_path}</cyan>')
