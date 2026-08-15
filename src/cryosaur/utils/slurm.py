'''
CRYOSAUR: SLURM scheduler models
'''

# -- Import external dependencies
from pydantic import BaseModel, Field

# -- SlurmResourceProfile: resource request for a single SLURM job
class SlurmResourceProfile(BaseModel):
    name: str = 'cryosaur_job'
    partition: str
    nodes: int = 1
    ntasks: int = 1
    cpus_per_task: int = 1
    gpus: int = 0
    mem: str | None = None
    mem_per_cpu: str | None = None
    mem_per_gpu: str | None = None
    time: str = '24:00:00'
    modules: list[str] = Field(default_factory=list)
