'''
CRYOSAUR: input/output utilities
'''

# -- Import external dependencies
from pathlib import Path

# -- _resolve_abspath: returns a Path for the absolute path for a given path
def _resolve_abspath(path: Path):
    return path.expanduser().resolve()

# -- _is_writable: returns bool indicating if supplied directory is writable
def _is_writable(directory: Path):
    from os import access, W_OK
    directory = _resolve_abspath(directory)
    return access(directory, W_OK)

# -- _next_available_path: returns a Path that doesn't collide with existing files (incrementing number suffix as required) 
def _next_available_path(path: Path) -> Path:
    path = _resolve_abspath(path)
    # Check path doesn't exist
    if not path.exists():
        return path
    # Add numeric suffix and increment until no collision with existing files
    stem, suffix = path.stem, path.suffix
    counter = 1
    while True:
        candidate = path.with_name(f'{stem}_{counter}{suffix}')
        if not candidate.exists():
            return candidate
        counter += 1