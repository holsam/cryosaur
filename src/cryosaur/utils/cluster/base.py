'''
CRYOSAUR: base resource profile and scheduler backend abstractions
'''

# -- Import external dependencies
from abc import ABC, abstractmethod
from pathlib import Path
from pydantic import BaseModel, Field

# -- Import internal cryosaur utilities
from cryosaur.utils.cluster.status import ClusterStatus

# -- ResourceProfile: fields common to every scheduler; scheduler-specific fields are specified in subclass
class ResourceProfile(BaseModel):
    name: str = 'cryosaur_job'
    nodes: int = 1
    ntasks: int = 1
    cpus_per_task: int = 1
    time: str = '24:00:00'
    mem: str | None = None
    modules: list[str] = Field(default_factory=list)

# -- SchedulerBackend: bundles detection, script rendering and submission for one scheduler
class SchedulerBackend(ABC):
    name: str
    resource_profile_cls: type[ResourceProfile]

    @abstractmethod
    def is_available(self) -> bool:
        '''Return True if this scheduler's tooling is present'''

    @abstractmethod
    def in_job(self) -> bool:
        '''Return True if currently running inside a job (i.e. interactive/submitted job and not a login node)'''

    @abstractmethod
    def render_script(self, resources: ResourceProfile, commands: list[str], log_path: Path, *, array_over: list | None = None) -> str:
        '''Render a submission script for this scheduler'''

    @abstractmethod
    def submit(self, script_path: Path) -> str:
        '''Submit a rendered script and return the scheduler-assigned job id'''

    # -- write_script: renders and writes a script to disk, returning its path
    def write_script(self, resources: ResourceProfile, commands: list[str], script_path: Path, log_path: Path, *, array_over: list | None = None) -> Path:
        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_text(self.render_script(resources, commands, log_path, array_over=array_over))
        return script_path

    # -- check: returns this backend's current ClusterStatus
    def check(self) -> ClusterStatus:
        if not self.is_available():
            return ClusterStatus(recognised=True, scheduler=self.name, on_cluster=False)
        return ClusterStatus(
            recognised=True,
            scheduler=self.name,
            on_cluster=True,
            in_job=self.in_job(),
        )
