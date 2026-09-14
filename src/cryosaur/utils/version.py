'''
CRYOSAUR: print current cryosaur version to terminal
'''

# -- Import external dependencies
from importlib.metadata import version, PackageNotFoundError
from pathlib import Path

def resolve_version():
    try:
        __version__ = version('cryosaur')
    except PackageNotFoundError:
        try:
            import tomllib
            pyproject_path = Path(__file__).parent.parent.parent.parent / 'pyproject.toml'
            with open(pyproject_path, 'rb') as f:
                data = tomllib.load(f)
            __version__ = data['project']['version']
        except:
            __version__ = None
    return __version__
