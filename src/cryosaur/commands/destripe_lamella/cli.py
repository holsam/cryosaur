'''
CRYOSAUR: `destripe-lamella` command CLI
'''

# -- Import external dependencies
import typer
from functools import partial
from typing import Annotated

# -- Import cryosaur utilities
from cryosaur.commands.destripe_lamella.plan import build_plan
from cryosaur.commands.destripe_lamella.validate import validate
from cryosaur.utils.cli.options import (
    ClusterResourcesOption,
    DryRunOption,
    ForkDirOption,
    FromStepOption,
    OnlyStepOption,
    SingleJobOption,
    SourceProjectArg,
)
from cryosaur.utils.cli.registry import register
from cryosaur.utils.cli.runner import run_command
from cryosaur.utils.relion_adapter.paths import derive_fork_dir
from cryosaur.utils.relion_adapter.rerun import resolve_steps_to_submit
from cryosaur.utils.relion_adapter.serialise import read_plan, write_plan
from cryosaur.utils.relion_adapter.submit import submit_plan, submit_steps

# -- Define ReuseAlignment option
ReuseAlignmentOption = Annotated[
    bool,
    typer.Option('--reuse-alignment/--realign', help='Reuse the source project\'s existing AreTomo3 alignment parameters rather than recomputing them from the destriped stack.', rich_help_panel='Branch Options'),
]

# -- _submit_single_job: adapts submit_plan's single_job path to run_command's expected shape
def _submit_single_job(plan) -> dict[str, str]:
    return submit_plan(plan, single_job=True)

# -- destripe_lamella_command: destripes per-tilt micrographs with PyLisC, then reconstructs, denoises and segments from the cleaned images, reusing the existing alignment
@register('destripe-lamella', panel='Pipelines')
def destripe_lamella_command(
    source: SourceProjectArg,
    fork_dir: ForkDirOption = None,
    dry_run: DryRunOption = False,
    reuse_alignment: ReuseAlignmentOption = True,
    single_job: SingleJobOption = False,
    from_step: FromStepOption = None,
    only_step: OnlyStepOption = None,
    cluster_resources: ClusterResourcesOption = None,
) -> None:
    '''
    Destripe per-tilt micrographs then reconstruct, denoise and segment using an existing alignment.
    '''
    run_command(
        derive_fork_dir=derive_fork_dir,
        build_plan=partial(build_plan, cluster_resources=cluster_resources, reuse_alignment=reuse_alignment),
        validate=validate,
        write_plan=write_plan,
        read_plan=read_plan,
        resolve_steps=resolve_steps_to_submit,
        submit_steps=submit_steps,
        submit_single_job=_submit_single_job,
        source=source,
        fork_dir=fork_dir,
        dry_run=dry_run,
        single_job=single_job,
        from_step=from_step,
        only_step=only_step,
    )
