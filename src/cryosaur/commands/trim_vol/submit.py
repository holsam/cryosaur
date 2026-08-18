'''
CRYOSAUR: submission for the trim-vol command
'''

# -- Import external dependencies
from pathlib import Path

# -- Import cryosaur utilities
from cryosaur.utils.cluster.cluster import build_cryosaur_command, get_backend
from cryosaur.utils.config import load_config, resolve_resources
from cryosaur.utils.errors import CryosaurError
from cryosaur.utils.log import log

# -- build_submission_script: writes one submission script for a single MRC via the named scheduler backend
def build_submission_script(
    mrc_path: Path,
    output_dir: Path,
    lowpass_radius: float,
    lowpass_sigma: float,
    lowpass_units: int,
    scheduler: str,
    cluster_resources: str | None = None,
) -> Path:
    backend = get_backend(scheduler.lower())
    if backend is None:
        raise CryosaurError(f'No {scheduler!r} backend registered')

    job_name = f'cryosaur-trim-{mrc_path.stem}'
    command = build_cryosaur_command(
        'trim',
        str(mrc_path),
        lowpass_radius=lowpass_radius,
        lowpass_sigma=lowpass_sigma,
        lowpass_units=lowpass_units,
        output_dir=str(output_dir),
    )

    resources = resolve_resources(load_config(), cluster_resources).model_copy(update={'name': job_name})
    script_path = output_dir / f'{mrc_path.stem}_trim.sbatch'
    log_path = output_dir / f'{mrc_path.stem}_trim.log'
    backend.write_script(resources, command, script_path, log_path)
    return script_path

# -- submit_job: submits a written script via the named scheduler backend, returning the job id
def submit_job(script_path: Path, scheduler: str) -> str:
    backend = get_backend(scheduler)
    if backend is None:
        raise CryosaurError(f'No {scheduler!r} backend registered')
    job_id = backend.submit(script_path)
    log.info(f'  <cyan>{script_path.stem}</cyan> -> {scheduler} job <cyan>{job_id}</cyan>')
    return job_id
