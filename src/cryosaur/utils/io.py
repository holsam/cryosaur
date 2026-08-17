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

# -- _find_files_by_extension: returns a list of Paths corresponding to files matching a given pattern
def _find_files_by_pattern(input_dir, pattern: str, recursive: bool = True):
    '''
    Find input files matching pattern within input_dir, recursing into subdirectories wher recursive=True
    '''
    glob = input_dir.rglob if recursive else input_dir.glob
    return sorted(p for p in glob(pattern))

# -- _find_files_by_extension: returns a list of Paths corresponding to files matching a given extension
def _find_files_by_extension(input_dir, extension: str, recursive: bool = True):
    '''
    Find input files with the extension '.extension' under input_dir, recursing into subdirectories when recursive=True
    '''
    extension = f'*{extension}' if extension.startswith('.') else f'*.{extension}'
    return _find_files_by_pattern(input_dir, extension, recursive)

# -- _resolve_input_paths: expands a file-or-directory argument to a sorted list of paths with given extension
def _resolve_input_paths(input_path: Path, extension: str) -> list[Path]:
    from cryosaur.utils.errors import CryosaurError
    if input_path.is_file():
        return [input_path]
    if input_path.is_dir():
        paths = _find_files_by_extension(input_dir=input_path, extension=extension)
        if not paths:
            raise CryosaurError(f'No <cyan>.{extension.lower()}</cyan> files found in <cyan>{input_path}</cyan>')
        return paths
    raise CryosaurError(f'<cyan>{input_path}</cyan> is neither a file nor a directory')
