'''
CRYOSAUR: TOML sidecar load/save for tomogram annotations
'''

# -- Import external dependencies
import tomllib, tomli_w
from pathlib import Path

# -- Import cryosaur utilities
from cryosaur.utils.log import log
from cryosaur.commands.viewer.utils.models import TomogramAnnotations

# -- annotations_path: returns the sidecar path for a given tomogram, e.g. tomo001.mrc -> tomo001.annotations.toml
def annotations_path(tomogram_path: Path) -> Path:
    return tomogram_path.parent / f'{tomogram_path.stem}.annotations.toml'

# -- load_annotations: returns the tomogram's annotations, or an empty set if no sidecar exists yet
def load_annotations(tomogram_path: Path) -> TomogramAnnotations:
    path = annotations_path(tomogram_path)
    if not path.exists():
        return TomogramAnnotations(tomogram_path=tomogram_path)
    with open(path, 'rb') as f:
        raw = tomllib.load(f)
    return TomogramAnnotations(**raw)

# -- save_annotations: writes the tomogram's annotations to its sidecar, returning the path written
def save_annotations(annotations: TomogramAnnotations) -> Path:
    path = annotations_path(annotations.tomogram_path)
    with open(path, 'wb') as f:
        tomli_w.dump(annotations.model_dump(mode='json'), f)
    log.debug(f'Saved annotations to <cyan>{path}</cyan>')
    return path
