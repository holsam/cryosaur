'''
CRYOSAUR: volume trimming pipeline
'''

# -- Import external dependencies
from dataclasses import dataclass
from pathlib import Path

# -- Import cryosaur utilities
from cryosaur.utils.external.imod import (
    TomopitchRecommendation,
    compute_trim_ranges,
    lowpass_filter,
    run_findsection_pitch,
    run_findsection_surface,
    run_flattenwarp,
    run_tomopitch,
    run_trimvol,
    run_warpvol,
)
from cryosaur.utils.log import log

# -- TrimResult: every intermediate and final path from one run of the pipeline, kept regardless of --preview so callers decide what to clean up
@dataclass
class TrimResult:
    source: Path
    filtered_for_surface: Path
    surface_model: Path
    warp_file: Path
    flattened: Path
    filtered_for_pitch: Path
    pitch_model: Path
    tomopitch_recommendation: TomopitchRecommendation
    trimmed: Path

# -- run_trim_pipeline: runs the volume trimming pipeline for a single MRC, writing intermediates into output_dir
def run_trim_pipeline(
    mrc_path: Path,
    output_dir: Path,
    lowpass_radius: float,
    lowpass_sigma: float,
    lowpass_units: int = 2,
) -> TrimResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = mrc_path.stem

    log.progress(f'<cyan>{stem}</cyan>: running lowpass filter for surface detection')
    filtered_for_surface = lowpass_filter(mrc_path, output_dir / f'{stem}_lowpass_surface.mrc', lowpass_radius, lowpass_sigma, lowpass_units)
    log.progress(f'<cyan>{stem}</cyan>: running findsection surface')
    surface_model = run_findsection_surface(filtered_for_surface, output_dir / f'{stem}_surface.mod')
    log.progress(f'<cyan>{stem}</cyan>: running flattenwarp')
    warp_file = run_flattenwarp(surface_model, output_dir / f'{stem}_warp.xf')
    log.progress(f'<cyan>{stem}</cyan>: running warpvol')
    flattened = run_warpvol(mrc_path, warp_file, output_dir / f'{stem}_flattened.mrc')

    log.progress(f'<cyan>{stem}</cyan>: running lowpass filter for pitch detection')
    filtered_for_pitch = lowpass_filter(flattened, output_dir / f'{stem}_lowpass_pitch.mrc', lowpass_radius, lowpass_sigma, lowpass_units)
    log.progress(f'<cyan>{stem}</cyan>: running findsection pitch')
    pitch_model = run_findsection_pitch(filtered_for_pitch, output_dir / f'{stem}_pitch.mod')
    log.progress(f'<cyan>{stem}</cyan>: running tomopitch')
    recommendation = run_tomopitch(pitch_model)
    x_range, y_range, z_range = compute_trim_ranges(flattened, recommendation)
    log.progress(f'<cyan>{stem}</cyan>: running trimvol {x_range=} {y_range=} {z_range=}')
    trimmed = run_trimvol(flattened, output_dir / f'{stem}_trimmed.mrc', x_range, y_range, z_range)

    return TrimResult(
        source=mrc_path,
        filtered_for_surface=filtered_for_surface,
        surface_model=surface_model,
        warp_file=warp_file,
        flattened=flattened,
        filtered_for_pitch=filtered_for_pitch,
        pitch_model=pitch_model,
        tomopitch_recommendation=recommendation,
        trimmed=trimmed,
    )
