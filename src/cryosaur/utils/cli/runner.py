'''
CRYOSAUR: pipeline orchestration logic
'''

# -- Import external dependencies
from collections.abc import Callable
from pathlib import Path
from typing import Any

# -- Import cryosaur utilities
from cryosaur.utils.errors import CryosaurError
from cryosaur.utils.log import log

# -- ValidationError: raised when a command's validation reports problems
class ValidationError(CryosaurError):
    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__('\n'.join(f'  - {p}' for p in problems))

# -- run_command: implements the pipeline workflow (plan->validate->write->validate->submit) 
def run_command(
    *,
    derive_fork_dir: Callable[[Path], Path],
    build_plan: Callable[[Path, Path], Any],
    validate: Callable[[Any], list[str]],
    write_plan: Callable[[Any], Path],
    read_plan: Callable[[Path], Any],
    resolve_steps: Callable[..., list[Any]],
    submit_steps: Callable[[list[Any]], dict[str, str]],
    submit_single_job: Callable[[Any], dict[str, str]],
    source: Path,
    fork_dir: Path | None,
    dry_run: bool,
    single_job: bool,
    from_step: str | None,
    only_step: str | None,
) -> None:
    if fork_dir is None:
        fork_dir = derive_fork_dir(source)
    log.info(f'Branching from <cyan>{source}</cyan> into <cyan>{fork_dir}</cyan>')

    if from_step or only_step:
        plan = read_plan(fork_dir)
        steps = resolve_steps(plan, from_step=from_step, only_step=only_step)
    else:
        plan = build_plan(source, fork_dir)
        problems = validate(plan)
        if problems:
            raise ValidationError(problems)
        write_plan(plan)
        steps = plan.steps

    if dry_run:
        log.info('--dry-run supplied: plan written, nothing submitted.')
        return

    # Re-validate immediately before submission, in case anything changed
    # since the plan was built or last written.
    problems = validate(plan)
    if problems:
        raise ValidationError(problems)

    if single_job and not (from_step or only_step):
        job_ids = submit_single_job(plan)
    else:
        job_ids = submit_steps(steps)

    for name, job_id in job_ids.items():
        log.info(f'  <cyan>{name}</cyan> -> SLURM job <cyan>{job_id}</cyan>')