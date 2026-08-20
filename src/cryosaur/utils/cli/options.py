'''
CRYOSAUR: shared CLI options for commands
'''

# -- Import external dependencies
import typer
from pathlib import Path
from typing import Annotated

# -- SourceProjectArg: argument expecting Path
SourceProjectArg = Annotated[
    Path,
    typer.Argument(help='Path to an existing RELION5 tomography project.', exists=True),
]

# -- ForkDirOption: option expecting either Path or None
ForkDirOption = Annotated[
    Path | None,
    typer.Option('--fork-dir', help='Directory to write the branched pipeline results to (derived from the source path if omitted).', show_default=None, rich_help_panel='Pipeline Options'),
]

# -- DryRunOption: option expecting boolean
DryRunOption = Annotated[
    bool,
    typer.Option('--dry-run', help='Plan, validate and write everything, but do not submit.', show_default=False, rich_help_panel='Pipeline Options'),
]

# -- SingleJobOption: option expecting boolean
SingleJobOption = Annotated[
    bool,
    typer.Option('--single-job', help='Run a pipeline as one SLURM submission instead of a dependency chain.', show_default=False, rich_help_panel='Pipeline Options'),
]

# -- FromStepOption: option expecting string or None
FromStepOption = Annotated[
    str | None,
    typer.Option('--from', help='Re-submit this step and everything after it, using the existing plan.', show_default=False, rich_help_panel='Pipeline Options'),
]

# -- OnlyStepOption: option expecting string or None
OnlyStepOption = Annotated[
    str | None,
    typer.Option('--only', help='Re-submit just this step, using the existing plan.', show_default=False, rich_help_panel='Pipeline Options'),
]

# -- ClusterResourcesOption: option expecting string or None
ClusterResourcesOption = Annotated[
    str | None,
    typer.Option('--cluster-resources', help="Use a [cluster.resources.<id>] profile instead of the config's default resources.", show_default=False, rich_help_panel='Pipeline Options'),
]

# -- DbPathOption: option expecting Path or None
DbPathOption = Annotated[
    Path | None,
    typer.Option('--db-path', help="Path to the annotation SQLite database (defaults to the config's [project] db_path, or project.db next to config.toml).", show_default=False, rich_help_panel='Project Options'),
]
