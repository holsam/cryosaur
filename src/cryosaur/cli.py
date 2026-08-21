'''
CRYOSAUR: main CLI entrypoint
'''

# -- Import external dependencies
import typer
from pathlib import Path
from typing import Annotated, Literal

# -- Import cryosaur utilities
from cryosaur.utils.errors import handle_errors
from cryosaur.utils.log import configure_logging, log
from cryosaur.utils.cli.registry import registered_commands

# -- Import cryosaur commands
import cryosaur.commands

# -- Initialise Typer class for cryosaur CLI
cryosaur = typer.Typer(
    add_completion=False,
    rich_markup_mode='rich',
    no_args_is_help=True,
    help='Resources and scripts for investigating ultrastructure using [italic]in situ[/] cryoEM 🦖'
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
        int,
        typer.Option('-q', '--quiet', count=True, help='Decrease verbosity of logging.', show_default=False, rich_help_panel='Logging Options', metavar='')
    ] = 0,
    verbosity: Annotated[
        int,
        typer.Option('-v', '--verbose', count=True, help='Increase verbosity of logging.', show_default=False, rich_help_panel='Logging Options', metavar='')
    ] = 0,
):
    # Check quiet and verbose haven't been supplied together
    if quiet and verbosity:
        raise typer.BadParameter('-q/--quiet and -v/--verbose are mutually exclusive.')
    # Default verbosity is 2 ('INFO'), so clamp both quiet and verbose to max of 2
    verbosity = 2 if verbosity > 2 else verbosity
    quiet = 2 if quiet > 2 else quiet
    # Configure logging
    log_path = configure_logging(directory=log_dir, mode=log_mode, quiet=quiet, verbosity=verbosity)
    # Output confirmation message that logging has been set up
    log.info(f'Log messages will be {"appended" if log_mode == 'append' else "written"} to <cyan>{log_path}</cyan>')

# -- _GROUP_HELP: dictionary containing help text for any sub-Typers 
_GROUP_HELP = {
    'utils': 'Misc cryosaur utilities.',
    'internal': 'Internal cryosaur commands.',
    'config': 'Manage the cryosaur configuration file.',
    'project': 'cryosaur project management commands.'
}

# -- _GROUP_HELP_PANELS: dictionary containing Rich help panels for any sub-Typers 
_GROUP_HELP_PANELS = {
    'utils': 'Utilities',
    'internal': 'Utilities',
    'config': 'Utilities',
    'project': 'Projects'
}

# -- Attach every registered command onto the main Typer app, grouping any with a `group` set under their own nested Typer app
_group_apps: dict[str, typer.Typer] = {}

for _name, _registered in registered_commands().items():
    _wrapped = handle_errors(_registered.func)
    if _registered.group is None:
        cryosaur.command(name=_name, hidden=_registered.hidden, rich_help_panel=_registered.panel)(_wrapped)
    else:
        if _registered.group not in _group_apps:
            _group_apps[_registered.group] = typer.Typer(no_args_is_help=True)
            cryosaur.add_typer(_group_apps[_registered.group], name=_registered.group, help=_GROUP_HELP.get(_registered.group, ''), rich_help_panel=_GROUP_HELP_PANELS.get(_registered.group))
        _group_apps[_registered.group].command(name=_name, hidden=_registered.hidden, rich_help_panel=_registered.panel)(_wrapped)
