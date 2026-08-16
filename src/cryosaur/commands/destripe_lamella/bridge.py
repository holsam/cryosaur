'''
CRYOSAUR: bridging STAR construction for destripe-lamella command
'''

# -- Import external dependencies
from pathlib import Path

# -- Import cryosaur utilities
from cryosaur.utils.errors import CryosaurError
from cryosaur.utils.log import log
from cryosaur.utils.relion_adapter.plan import BridgingContract

# -- BridgingAssertionError: raised when a BridgingContract declaration doesn't match what was actually written
class BridgingAssertionError(CryosaurError):
    pass

# -- parse_tilt_series_star_loop: returns (column_names, rows) for the single loop_ block in a simple, one-block STAR file
def parse_tilt_series_star_loop(path: Path) -> tuple[list[str], list[list[str]]]:
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

# -- write_tilt_series_star_loop: writes a single data_<name>/loop_ STAR block
def write_tilt_series_star_loop(path: Path, *, data_name: str, columns: list[str], rows: list[list[str]]) -> None:
    lines = [f'data_{data_name}', 'loop_']
    lines += [f'_{column}' for column in columns]
    lines += [' '.join(row) for row in rows]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(lines) + '\n')

# -- build_bridging_star: copies and repoints the source project's AlignTiltSeries output into the fork, returning the path to the new top-level tilt series STAR
def build_bridging_star(
    *,
    source_project: Path,
    source_aligned_tilt_series: Path,
    fork_dir: Path,
    fork_job_dir: Path,
    destriped_micrograph_for: dict[tuple[str, str], str],
    contract: BridgingContract,
) -> Path:
    '''
    destriped_micrograph_for maps (tomogram_name, original_micrograph_path) to the destriped replacement path (both relative to their respective project roots)
    '''
    if not (contract.preserves_tilt_count and contract.preserves_tilt_order and contract.preserves_alignment):
        raise CryosaurError('build_bridging_star is not compatible with commands that do not preserve tilt count, order and/or alignment')

    top_columns, top_rows = parse_tilt_series_star_loop(source_aligned_tilt_series)
    star_file_column = top_columns.index('rlnTomoTiltSeriesStarFile')
    name_column = top_columns.index('rlnTomoName')

    fork_tilt_series_dir = fork_job_dir / 'tilt_series'
    new_top_rows: list[list[str]] = []

    for row in top_rows:
        tomo_name = row[name_column]
        source_per_tomo_path = source_project / row[star_file_column]
        new_per_tomo_path = fork_tilt_series_dir / f'{tomo_name}.star'
        _bridge_per_tomogram_star(
            source_path=source_per_tomo_path,
            output_path=new_per_tomo_path,
            tomo_name=tomo_name,
            destriped_micrograph_for=destriped_micrograph_for,
            contract=contract,
        )
        new_row = list(row)
        new_row[star_file_column] = str(new_per_tomo_path.relative_to(fork_dir))
        new_top_rows.append(new_row)

    output_path = fork_job_dir / 'aligned_tilt_series.star'
    write_tilt_series_star_loop(output_path, data_name='global', columns=top_columns, rows=new_top_rows)
    log.debug(f'Wrote bridging tilt series STAR to <cyan>{output_path}</cyan>')
    return output_path

# -- _bridge_per_tomogram_star: copies one per-tomogram STAR file repointing _rlnMicrographName at destriped images
def _bridge_per_tomogram_star(
    *,
    source_path: Path,
    output_path: Path,
    tomo_name: str,
    destriped_micrograph_for: dict[tuple[str, str], str],
    contract: BridgingContract,
) -> None:
    columns, rows = parse_tilt_series_star_loop(source_path)
    micrograph_column = columns.index('rlnMicrographName')

    new_rows: list[list[str]] = []
    for row in rows:
        original_micrograph = row[micrograph_column]
        key = (tomo_name, original_micrograph)
        if key not in destriped_micrograph_for:
            raise BridgingAssertionError(f'No destriped replacement found for {original_micrograph} (tomogram {tomo_name})')
        new_row = list(row)
        new_row[micrograph_column] = destriped_micrograph_for[key]
        new_rows.append(new_row)

    if contract.preserves_tilt_count and len(new_rows) != len(rows):
        raise BridgingAssertionError(f'{tomo_name}: contract declares preserves_tilt_count=True but wrote {len(new_rows)} rows from {len(rows)} source rows')
    if contract.preserves_tilt_order:
        angle_column = columns.index('rlnTomoNominalStageTiltAngle')
        source_order = [row[angle_column] for row in rows]
        new_order = [row[angle_column] for row in new_rows]
        if source_order != new_order:
            raise BridgingAssertionError(f'{tomo_name}: contract declares preserves_tilt_order=True but tilt angle ordering changed')

    write_tilt_series_star_loop(output_path, data_name=tomo_name, columns=columns, rows=new_rows)