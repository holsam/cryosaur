'''
CRYOSAUR: IMOD tool wrappers
'''

# -- Import external dependencies
import mrcfile, re, subprocess
from dataclasses import dataclass
from pathlib import Path

# -- Import cryosaur utilities
from cryosaur.utils.errors import CryosaurError
from cryosaur.utils.log import log

# -- _run: runs an IMOD command, raising CryosaurError with stderr on failure
def _run(command: list[str]) -> subprocess.CompletedProcess:
    log.debug(f'Running {" ".join(command)}')
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        log.error(f'{command[0]} failed: {result.stderr.strip()}')
        raise CryosaurError(f'{command[0]} failed: {result.stderr.strip()}')
    return result

# -- lowpass_filter: transient low-pass filter
def lowpass_filter(
    input_path: Path,
    output_path: Path,
    radius: float,
    sigma: float,
    units: int = 2,
) -> Path:
    _run([
        'mtffilter',
        '-input', str(input_path),
        '-output', str(output_path),
        '-lowpass', str(radius), str(sigma),
        '-units', str(units),
    ])
    return output_path

# -- run_findsection_surface: estimates a surface model for flattenwarp, from a (filtered) volume
def run_findsection_surface(input_path: Path, surface_path: Path) -> Path:
    _run([
        'findsection',
        '-tomo', str(input_path),
        '-surface', str(surface_path),
    ])
    return surface_path

# -- run_findsection_pitch: estimates a boundary/pitch model, from a (filtered) volume
def run_findsection_pitch(input_path: Path, pitch_path: Path) -> Path:
    _run([
        'findsection',
        '-tomo', str(input_path),
        '-pitch', str(pitch_path),
    ])
    return pitch_path

# -- run_flattenwarp: computes a warp transform from a findsection surface model
def run_flattenwarp(surface_path: Path, warp_path: Path) -> Path:
    _run([
        'flattenwarp',
        '-input', str(surface_path),
        '-output', str(warp_path),
    ])
    return warp_path

# -- run_warpvol: applies a warp transform to the unfiltered volume
def run_warpvol(input_path: Path, warp_path: Path, output_path: Path) -> Path:
    _run([
        'warpvol',
        '-input', str(input_path),
        '-xforms', str(warp_path),
        '-output', str(output_path),
    ])
    return output_path

# -- TomopitchRecommendation: tomopitch's recommended thickness, Z-shift, angle offset and X-axis tilt
@dataclass
class TomopitchRecommendation:
    thickness: float
    z_shift: float
    angle_offset: float
    x_axis_tilt: float

# -- parse_tomopitch_output: extracts the recommended thickness/Z-shift/angle-offset/X-axis-tilt line from tomopitch's stdout
def parse_tomopitch_output(stdout_text: str) -> TomopitchRecommendation:
    match = re.search(
        r'Recommended thickness,\s*Z-shift,\s*angle offset,\s*and X-axis tilt:'
        r'\s*(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)',
        stdout_text,
    )
    if not match:
        log.error(f'Could not parse tomopitch output:\n{stdout_text}')
        raise CryosaurError(f'Could not parse tomopitch output:\n{stdout_text}')
    thickness, z_shift, angle_offset, x_axis_tilt = (float(g) for g in match.groups())
    return TomopitchRecommendation(
        thickness=thickness,
        z_shift=z_shift,
        angle_offset=angle_offset,
        x_axis_tilt=x_axis_tilt,
    )

# -- run_tomopitch: runs tomopitch on a findsection pitch model, returns the parsed recommendation
def run_tomopitch(pitch_model_path: Path) -> TomopitchRecommendation:
    result = _run(['tomopitch', '-model', str(pitch_model_path)])
    return parse_tomopitch_output(result.stdout)

# -- compute_trim_ranges: turns a tomopitch recommendation into trimvol's x/y/z start-end ranges
def compute_trim_ranges(volume_path: Path, recommendation: TomopitchRecommendation) -> tuple[tuple[int, int], tuple[int, int], tuple[int, int]]:
    with mrcfile.open(volume_path, header_only=True, permissive=True) as mrc:
        nx, ny, nz = int(mrc.header.nx), int(mrc.header.ny), int(mrc.header.nz)

    z_center = nz / 2 + recommendation.z_shift
    z_start = int(round(z_center - recommendation.thickness / 2))
    z_end = int(round(z_center + recommendation.thickness / 2))

    x_range = (0, nx - 1)
    y_range = (0, ny - 1)
    z_range = (max(z_start, 0), min(z_end, nz - 1))
    if z_range != (z_start, z_end):
        log.debug(f'Clamped z range from ({z_start}, {z_end}) to {z_range} (volume nz={nz})')
    return x_range, y_range, z_range

# -- run_trimvol: crops to explicit X/Y/Z start-end ranges
def run_trimvol(
    input_path: Path,
    output_path: Path,
    x_range: tuple[int, int],
    y_range: tuple[int, int],
    z_range: tuple[int, int],
) -> Path:
    _run([
        'trimvol',
        '-x', str(x_range[0]), str(x_range[1]),
        '-y', str(y_range[0]), str(y_range[1]),
        '-z', str(z_range[0]), str(z_range[1]),
        str(input_path),
        str(output_path),
    ])
    return output_path
