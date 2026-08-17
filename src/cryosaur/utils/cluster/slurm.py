'''
CRYOSAUR: SLURM scheduler backend
'''

# -- Import external dependencies
import os, re, shutil, subprocess
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

# -- Import internal cryosaur utilities
from cryosaur.utils.cluster.base import ResourceProfile, SchedulerBackend
from cryosaur.utils.errors import CryosaurError
from cryosaur.utils.log import log

# -- Define path to template directory and load to _env
_TEMPLATE_DIR = Path(__file__).parent / 'templates'
_env = Environment(
    loader=FileSystemLoader(_TEMPLATE_DIR),
    trim_blocks=True,
    lstrip_blocks=True,
    autoescape=select_autoescape(disabled_extensions=('j2',)),
)

# -- SlurmResourceProfile: resource request for a single SLURM job
class SlurmResourceProfile(ResourceProfile):
    partition: str
    gpus: int = 0
    mem_per_cpu: str | None = None
    mem_per_gpu: str | None = None

# -- SlurmBackend: SchedulerBackend implementation for SLURM
class SlurmBackend(SchedulerBackend):
    name = 'slurm'
    resource_profile_cls = SlurmResourceProfile

    def is_available(self) -> bool:
        if shutil.which('sinfo') is None:
            return False
        try:
            subprocess.run(['sinfo'], capture_output=True, timeout=5, check=True)
            return True
        except (subprocess.SubprocessError, OSError):
            return False

    def in_job(self) -> bool:
        return 'SLURM_JOB_ID' in os.environ

    def render_script(self, resources: SlurmResourceProfile, command: str, log_path: Path) -> str:
        template = _env.get_template('slurm_script.sh.j2')
        return template.render(resources=resources, command=command, log_path=log_path)

    # -- submit: runs sbatch on a rendered script and returns the job id
    def submit(self, script_path: Path) -> str:
        try:
            result = subprocess.run(
                ['sbatch', str(script_path)],
                capture_output=True, text=True, timeout=30, check=True,
            )
        except (subprocess.SubprocessError, OSError) as exc:
            log.error(f'sbatch submission failed for {script_path}: {exc}')
            raise CryosaurError(f'sbatch submission failed for {script_path}') from exc
        match = re.search(r'Submitted batch job (\d+)', result.stdout)
        if not match:
            raise CryosaurError(f'Could not parse job id from sbatch output: {result.stdout!r}')
        return match.group(1)
