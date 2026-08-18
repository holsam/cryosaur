'''
CRYOSAUR: check for installed tools needed by cryosaur
'''

# -- Import external dependencies
import typer
from dataclasses import dataclass
from rich.console import Console
from rich.table import Table
from shutil import which
from typing import Annotated, List

# -- Import cryosaur utilties
from cryosaur.utils.cli.registry import register

# -- Dependency: dataclass holding information about a given dependency
@dataclass
class Dependency:
    name: str
    binary: str
    install_hint: str = ''
    
    @property
    def available(self) -> bool:
        return which(self.binary) is not None

# -- _COMMAND_DEPENDENCIES: dictionary containing each requirement for a cryosaur command
# TODO: check destripe_lamella
_COMMAND_DEPENDENCIES: dict[str, list[Dependency]] = {
    'destripe-lamella': [
        Dependency('PyLisC', 'pylisc', 'uv tool install git+https://github.com/holsam/pylisc'),
        Dependency('CCP-EM Pipeliner', 'pipeliner', 'uv tool install git+https://gitlab.com/ccpem/ccpem-pipeliner'),
        Dependency('RELION5', 'relion', ''),
        Dependency('Topaz', 'topaz', ''),
        Dependency('MemBrain-Seg', 'membrain', ''),
    ],
    'trim-vol': [
        Dependency('mtffilter (IMOD)', 'mtffilter', 'install IMOD'),
        Dependency('findsection (IMOD)', 'findsection', 'install IMOD'),
        Dependency('flattenwarp (IMOD)', 'flattenwarp', 'install IMOD'),
        Dependency('warpvol (IMOD)', 'warpvol', 'install IMOD'),
        Dependency('tomopitch (IMOD)', 'tomopitch', 'install IMOD'),
        Dependency('trimvol (IMOD)', 'trimvol', 'install IMOD'),
    ],
}

# -- print_dependency_table: create a rich Console and print each command with dependency availability 
def print_dependency_table(commands):
    console = Console(width=90)
    for command in commands:
        console.print()
        deps = _COMMAND_DEPENDENCIES.get(command, [])
        if not deps:
            continue
        none_missing = all(dep.available for dep in deps)
        header_style= 'green' if none_missing else 'red'
        console.rule(f'[bold]{"[green]✔[/green]" if none_missing else "[red]✘[/red]"} {command}[/bold]', style=header_style)
        table = Table(show_header=True, box=None, pad_edge=False)
        table.add_column("Dependency")
        table.add_column("Status", justify='center')
        table.add_column("Installation Hint", style='dim')
        for dep in deps:
            status = "[bold green]✔[/]" if dep.available else "[bold red]✘[/]"
            hint = '' if dep.available else dep.install_hint
            table.add_row(dep.name, status, hint)
        console.print(table)

@register('check-tools', group='utils')
def check_external_tools(
    commands: Annotated[
        List[str] | None,
        typer.Argument(help='Specify commands to check.', show_default=False)
    ] = None,
):
    '''
    Check PATH for tools required by each cryosaur command.
    '''
    # If no commands specified, assume all
    if commands is None:
        commands = list(_COMMAND_DEPENDENCIES.keys())
    # Print table
    print_dependency_table(commands)
