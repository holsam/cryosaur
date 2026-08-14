'''
CRYOSAUR: main CLI entrypoint
'''

# -- Import external dependencies
import typer

# -- Initialise Typer class for cryosaur CLI
cryosaur = typer.Typer(
    add_completion=False,
    rich_markup_mode='rich',
    no_args_is_help=True,
)
