'''
CRYOSAUR: SLURM script rendering
'''

# -- Import external dependencies
from pathlib import Path

# -- Import cryosaur utilities
from cryosaur.utils.cluster.slurm import SlurmBackend
from cryosaur.utils.relion_adapter.plan import PlannedStep

_backend = SlurmBackend()

# -- write_slurm_script: renders and writes a step's SLURM submission script into its job directory, returning the script path
def write_slurm_script(step: PlannedStep) -> Path:
    resources = step.resources.model_copy(update={'name': step.name})
    log_path = step.job_dir / f'{step.name}.log'
    script_path = step.job_dir / f'{step.name}.sh'
    return _backend.write_script(resources, step.commands, script_path, log_path, array_over=step.array_over)