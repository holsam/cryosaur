'''
CRYOSAUR: cluster/scheduler detection and command building
'''

# -- Import external dependencies
from pathlib import Path
from typing import Callable, Optional

# -- Import internal cryosaur utilities
from cryosaur.utils.cluster.base import SchedulerBackend
from cryosaur.utils.cluster.slurm import SlurmBackend, _default_slurm_cpu_resources, _default_slurm_gpu_resources
from cryosaur.utils.cluster.status import ClusterStatus
from cryosaur.utils.errors import CryosaurError
from cryosaur.utils.log import log

# -- _BACKENDS: registry containing all known scheduler backends
_BACKENDS: dict[str, SchedulerBackend] = {
    'slurm': SlurmBackend(),
}

# -- _DEFAULT_RESOURCE_FACTORIES: one default-resource builder per registered scheduler backend
_DEFAULT_RESOURCE_FACTORIES_KEYS = ('slurm_cpu', 'slurm_gpu')
_DEFAULT_RESOURCE_FACTORIES: dict[str, Callable[[str], ResourceProfile]] = {
    'slurm_cpu': _default_slurm_cpu_resources,
    'slurm_gpu': _default_slurm_gpu_resources,
}

# -- get_backend: looks up a registered scheduler backend by name
def get_backend(scheduler: str) -> SchedulerBackend | None:
    return _BACKENDS.get(scheduler)

# -- default_resources: looks up the default resource profile for a resources_id, raising if none is known
def default_resources(resources_id: str, job_name: str) -> ResourceProfile:
    factory = _DEFAULT_RESOURCE_FACTORIES.get(resources_id)
    if factory is None:
        raise CryosaurError(f'No default resource profile for scheduler {resources_id!r}; pass resources explicitly.')
    return factory(job_name)

# -- check_cluster: returns ClusterStatus corresponding to current state
def check_cluster(scheduler: Optional[str] = None) -> ClusterStatus:
    '''Checks for cluster/job status, using the given scheduler if present or against all schedulers otherwise'''
    if scheduler is not None:
        backend = get_backend(scheduler)
        if backend is None:
            return ClusterStatus(recognised=False, message=f'Unrecognised scheduler {scheduler}; checks could not run')
        return backend.check()
    for backend in _BACKENDS.values():
        status = backend.check()
        if status.on_cluster:
            return status
    return ClusterStatus(recognised=True, on_cluster=False)

# -- confirm_local_run: prompts before running a command locally on what looks like a cluster login node
def confirm_local_run(command: str) -> None:
    status = check_cluster()
    if status.on_cluster and not status.in_job:
        proceed = log.input(
            'cryosaur appears to be running on a cluster login node. Continue with processing',
            options=['y', 'n'], default='n', case_sensitive=False,
        )
        if not proceed:
            raise CryosaurError(f'cryosaur {command} aborted: run inside an interactive job, or pass --cluster')

# -- build_cryosaur_command: builds 'cryosaur <subcommand> <positional...> --flag value ...'
# Keyword flags convert snake_case to --kebab-case; True emits a bare flag; False and None are omitted entirely; everything else is stringified
def build_cryosaur_command(subcommand: str, *positional: str | Path, **flags) -> str:
    parts = ['cryosaur', subcommand, *(str(p) for p in positional)]
    for key, value in flags.items():
        if value is None or value is False:
            continue
        flag = '--' + key.replace('_', '-')
        if value is True:
            parts.append(flag)
            continue
        parts.append(flag)
        parts.append(str(value))
    return ' '.join(parts)
