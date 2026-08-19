'''
CRYOSAUR: user configuration management
'''

# -- Import external dependencies
import tomllib, typer
from pathlib import Path
from pydantic import BaseModel, Field

# -- Import cryosaur utilities
from cryosaur.utils.cluster.base import ResourceProfile
from cryosaur.utils.cluster.cluster import get_backend
from cryosaur.utils.errors import CryosaurError
from cryosaur.utils.log import log

# -- CONFIG_DIR: location of directory for config files
CONFIG_DIR = Path(typer.get_app_dir('cryosaur'))
# -- CONFIG_PATH: location of cryosaur config file
CONFIG_PATH = CONFIG_DIR / 'config.toml'

# -- ClusterSection: config.toml's [cluster] section
class ClusterSection(BaseModel):
    scheduler: str
    default_resources: str | None = None
    modules: dict[str, str] = Field(default_factory=dict)
    resources: dict[str, ResourceProfile] = Field(default_factory=dict)

# -- CryosaurConfig: parsed config.toml
class CryosaurConfig(BaseModel):
    cluster: ClusterSection

# -- _resolve_modules: replaces a resource profile's `modules` keys with their real module strings from [cluster.modules], raising on an unknown key
def _resolve_modules(modules: list[str], module_table: dict[str, str], resources_id: str) -> list[str]:
    resolved = []
    for key in modules:
        if key not in module_table:
            raise CryosaurError(f'{CONFIG_PATH}: [cluster.resources.{resources_id}] references unknown module {key!r} (not found in [cluster.modules])')
        resolved.append(module_table[key])
    return resolved

# -- load_config: parses CONFIG_PATH, resolving module references and validating each resource profile against its scheduler's own profile type, returning None if no config file exists
def load_config() -> CryosaurConfig | None:
    if not CONFIG_PATH.exists():
        log.debug(f'No config file at {CONFIG_PATH}')
        return None
    with open(CONFIG_PATH, 'rb') as f:
        raw = tomllib.load(f)
    log.debug(f'Loaded config from <cyan>{CONFIG_PATH}</cyan>')  

    cluster_raw = dict(raw.get('cluster', {}))
    module_table = cluster_raw.get('modules', {})
    resources_raw = dict(cluster_raw.get('resources', {}))

    scheduler = cluster_raw.get('scheduler')
    backend = get_backend(scheduler) if scheduler else None
    log.debug(f'Resolved scheduler={scheduler!r} backend={backend}')
    if resources_raw and backend is None:
        log.error(f'{CONFIG_PATH}: unrecognised scheduler {scheduler!r}')
        raise CryosaurError(f'{CONFIG_PATH}: unrecognised or missing [cluster] scheduler {scheduler!r}; cannot validate [cluster.resources]')

    resolved_resources: dict[str, ResourceProfile] = {}
    for resources_id, profile in resources_raw.items():
        profile = dict(profile)
        if 'modules' in profile:
            profile['modules'] = _resolve_modules(profile['modules'], module_table, resources_id)
        try:
            resolved_resources[resources_id] = backend.resource_profile_cls(**profile)
        except Exception as exc:
            log.error(f'Invalid [cluster.resources.{resources_id}]: {exc}')
            raise CryosaurError(f'{CONFIG_PATH}: invalid [cluster.resources.{resources_id}] - {exc}') from exc
    cluster_raw['resources'] = resolved_resources

    try:
        return CryosaurConfig(cluster=cluster_raw)
    except Exception as exc:
        log.error(f'Invalid config: {exc}')
        raise CryosaurError(f'{CONFIG_PATH}: invalid config - {exc}') from exc

# -- resolve_resources: returns the ResourceProfile to use as a baseline, honouring an explicit override over the config's default_resources, raising a clear error if neither is available
def resolve_resources(config: CryosaurConfig | None, override_id: str | None) -> ResourceProfile:
    if config is None:
        raise CryosaurError(f'No cryosaur config found at {CONFIG_PATH}. Run `cryosaur config init` first')

    resources_id = override_id or config.cluster.default_resources
    if resources_id is None:
        raise CryosaurError(f'{CONFIG_PATH}: no [cluster] default_resources set, and no --cluster-resources given')

    profile = config.cluster.resources.get(resources_id)
    if profile is None:
        raise CryosaurError(f'{CONFIG_PATH}: no [cluster.resources.{resources_id}] section defined')
    return profile
