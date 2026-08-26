'''
CRYOSAUR: reading RELION5 per-tomogram tilt series STAR files
'''

# -- Import external dependencies
from pathlib import Path

# -- Import cryosaur utilities
from cryosaur.utils.errors import CryosaurError

# -- parse_star_loop: returns (column_names, rows) for the single loop_ block in a simple, one-block STAR file
def parse_star_loop(path: Path) -> tuple[list[str], list[list[str]]]:
    lines = path.read_text().splitlines()
    columns: list[str] = []
    rows: list[list[str]] = []
    in_loop = False
    reading_columns = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith('loop_'):
            in_loop = True
            reading_columns = True
            continue
        if not in_loop:
            continue
        if reading_columns:
            if stripped.startswith('_'):
                columns.append(stripped.lstrip('_').split()[0])
                continue
            reading_columns = False
        rows.append(stripped.split())
    return columns, rows

# -- read_tomogram_micrographs: returns the rlnMicrographName column of tilt_series_star_path, in file order (RELION's own deduplicated tilt order — do not re-sort)
def read_tomogram_micrographs(tilt_series_star_path: Path) -> list[str]:
    columns, rows = parse_star_loop(tilt_series_star_path)
    if 'rlnMicrographName' not in columns:
        raise CryosaurError(f'{tilt_series_star_path}: no rlnMicrographName column found')
    micrograph_column = columns.index('rlnMicrographName')
    return [row[micrograph_column] for row in rows]
