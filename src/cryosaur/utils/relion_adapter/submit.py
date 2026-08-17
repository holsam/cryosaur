'''
CRYOSAUR: SLURM submission logic
'''

# -- Import external dependencies
import subprocess
from pathlib import Path

# -- Import cryosaur utilities
from cryosaur.utils.errors import CryosaurError
from cryosaur.utils.log import log
from cryosaur.utils.relion_adapter.plan import PlannedStep, RunPlan
from cryosaur.utils.relion_adapter.slurm import write_slurm_script

# -- SubmissionError: raised when sbatch fails or returns an unparsable job id
class SubmissionError(CryosaurError):
    pass

# -- _submit_step: submits a single step's script via sbatch, returning its SLURM job id
def _submit_step(step: PlannedStep, *, depends_on: list[str] | None = None) -> str:
    script_path = write_slurm_script(step)
    command = ['sbatch', '--parsable']
    if depends_on:
        command += ['--dependency', 'afterok:' + ':'.join(depends_on)]
    command.append(str(script_path))
    log.progress(f'Submitting <cyan>{step.name}</cyan>: {" ".join(command)}')
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise SubmissionError(f'sbatch failed for step {step.name!r}: {result.stderr.strip()}')
    job_id = result.stdout.strip()
    if not job_id.isdigit():
        raise SubmissionError(f'Unexpected sbatch output for step {step.name!r}: {result.stdout!r}')
    log.debug(f'Submitted <cyan>{step.name}</cyan> as SLURM job <cyan>{job_id}</cyan>')
    return job_id


# -- submit_steps: submits a list of steps as a SLURM dependency chain (in the order given), returning step name to SLURM job id
def submit_steps(steps: list[PlannedStep]) -> dict[str, str]:
    job_ids: dict[str, str] = {}
    for step in steps:
        depends_on = [job_ids[name] for name in step.depends_on if name in job_ids]
        job_ids[step.name] = _submit_step(step, depends_on=depends_on)
    return job_ids


# -- render_single_job_script: returns a script that runs every step's commands sequentially in one submission
def render_single_job_script(steps: list[PlannedStep]) -> str:
    resources = steps[0].resources
    lines = ['#!/bin/bash', 'set -euo pipefail', '']
    lines.append(f'#SBATCH -p {resources.partition}')
    lines.append('#SBATCH -J "cryosaur-single-job"')
    lines.append(f'#SBATCH -t {resources.time}')
    if resources.gpus:
        lines.append(f'#SBATCH --gpus={resources.gpus}')
    lines.append(f'#SBATCH --cpus-per-task={resources.cpus_per_task}')
    if resources.mem_per_gpu:
        lines.append(f'#SBATCH --mem-per-gpu={resources.mem_per_gpu}')
    elif resources.mem_per_cpu:
        lines.append(f'#SBATCH --mem-per-cpu={resources.mem_per_cpu}')
    elif resources.mem:
        lines.append(f'#SBATCH --mem={resources.mem}')
    lines.append('')
    for module in resources.modules:
        lines.append(f'module load {module}')
    lines.append('')
    for step in steps:
        lines.append(f'# -- step: {step.name}')
        lines.extend(step.commands)
        lines.append('')
    return '\n'.join(lines)


# -- submit_single_job: submits every step as one sequential SLURM script, returning the single SLURM job id keyed by every step name
def submit_single_job(steps: list[PlannedStep], fork_dir: Path) -> dict[str, str]:
    script_path = fork_dir / 'cryosaur' / 'single_job.sh'
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(render_single_job_script(steps))
    result = subprocess.run(['sbatch', '--parsable', str(script_path)], capture_output=True, text=True)
    if result.returncode != 0:
        raise SubmissionError(f'sbatch failed for single-job submission: {result.stderr.strip()}')
    job_id = result.stdout.strip()
    return {step.name: job_id for step in steps}


# -- submit_plan: submits every step in a plan, honouring --single-job, returning step name to SLURM job id
def submit_plan(plan: RunPlan, *, single_job: bool = False) -> dict[str, str]:
    if single_job:
        return submit_single_job(plan.steps, plan.fork_dir)
    return submit_steps(plan.steps)
