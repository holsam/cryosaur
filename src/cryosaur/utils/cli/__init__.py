'''
CRYOSAUR: commands module
'''

# -- Import standard libraries
import re
from importlib.metadata import PackageNotFoundError, requires, version

_DISTRIBUTION_NAME = 'cryosaur'
# -- matches the `; extra == "name"` marker suffix on a PEP 508 requirement string
_EXTRA_MARKER_RE = re.compile(r';\s*extra\s*==\s*[\'"](?P<extra>[^\'"]+)[\'"]\s*$')
# -- matches the leading distribution name of a PEP 508 requirement string
_DIST_NAME_RE = re.compile(r'^([A-Za-z0-9][A-Za-z0-9._-]*)')

def _load_optional_dependency_groups() -> dict[str, list[str]]:
    '''
    Read the `extra == "..."` markers off cryosaur package's metadata, returning {group_name: [distribution_name, ...]}.
    '''
    groups: dict[str, list[str]] = {}
    for req_str in requires(_DISTRIBUTION_NAME) or []:
        marker_match = _EXTRA_MARKER_RE.search(req_str)
        if marker_match is None:
            continue
        name_match = _DIST_NAME_RE.match(req_str)
        if name_match is None:
            continue
        groups.setdefault(marker_match.group('extra'), []).append(name_match.group(1))
    return groups

def _group_installed(group: str, groups: dict[str, list[str]]) -> bool:
    for dist_name in groups.get(group, []):
        try:
            version(dist_name)
        except PackageNotFoundError:
            return False
    return True

_OPTIONAL_DEPENDENCY_GROUPS = _load_optional_dependency_groups()

# -- Define all commands with module path and any required dependency groups
# --    Format is: 'module.path': ('command appearance in cli', 'dependencygroup')
cryosaur_commands = {
    # project subcommands
    'cryosaur.commands.project.annotate': ('project annotate', 'project'),
    'cryosaur.commands.project.export_report': ('project export-report', None),
    'cryosaur.commands.project.import_toml': ('project import-toml', 'project'),
    'cryosaur.commands.project.ingest': ('project ingest-screenshots', 'project'),
    'cryosaur.commands.project.render': ('project render', None),
    'cryosaur.commands.project.session': (['session create', 'session list', 'session show', 'session delete'], None),
    'cryosaur.commands.project.view': ('project view', 'project'),
    # pipelines
    'cryosaur.commands.destripe_lamella.cli': ('destripe-lamella', None),
    'cryosaur.commands.morpho_analysis.cli': ('morpho-analysis', None),
    # tools
    'cryosaur.commands.trim_vol.cli': ('trim-vol', None),
    # utilities
    'cryosaur.commands.config.config': ('config', None),
    'cryosaur.commands.utils.check_external_tools': ('utils check-tools', None),
    'cryosaur.commands.utils.flatten': ('utils flatten', None),
}

# -- Initialise list to hold unavailable commands 
UNAVAILABLE_COMMANDS = []

# -- Loop over all commands: try to import, and check required optional-dependency group is installed
for command, (labels, group) in cryosaur_commands.items():
    if group is not None and not _group_installed(group, _OPTIONAL_DEPENDENCY_GROUPS):
        UNAVAILABLE_COMMANDS.extend(labels if isinstance(labels, list) else [labels])
        continue
    try:
        __import__(command)
    except (ModuleNotFoundError, ImportError):
        UNAVAILABLE_COMMANDS.extend(labels if isinstance(labels, list) else [labels])
