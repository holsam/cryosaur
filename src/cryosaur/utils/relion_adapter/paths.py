'''
CRYOSAUR: fork directory derivation
'''

# -- Import external dependencies
from pathlib import Path

# -- Import cryosaur utilities
from cryosaur.utils.errors import CryosaurError
from cryosaur.utils.io import _resolve_abspath

# -- ForkDirectoryError: raised when a fork directory cannot be derived from a source project path
class ForkDirectoryError(CryosaurError):
    pass

# -- derive_fork_dir: returns the default fork directory for a source RELION5 project, or raises ForkDirectoryError if the source path doesn't match the expected layout
def derive_fork_dir(source_project: Path) -> Path:
    source_project = _resolve_abspath(source_project)
    parts = source_project.parts
    try:
        processed_index = parts.index('processed')
    except ValueError:
        raise ForkDirectoryError(f'Could not derive a fork directory from {source_project}')
    remainder = parts[processed_index + 1 :]
    if len(remainder) < 2 or remainder[1] != 'relion_murfey':
        raise ForkDirectoryError(f'Could not derive a fork directory from {source_project}')
    collection = remainder[0]
    root = Path(*parts[:processed_index])
    return root / 'processing' / 'cryosaur' / collection / 'relion_murfey_cryosaur'
