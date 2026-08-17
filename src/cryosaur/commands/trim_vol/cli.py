'''
CRYOSAUR: trim-vol command CLI wiring
'''

# -- Import external dependencies
import typer
from pathlib import Path
from typing import Annotated

# -- Import cryosaur utilities
from cryosaur.commands.trim_vol.pipeline import run_trim_pipeline
from cryosaur.commands.trim_vol.preview import build_preview
from cryosaur.utils.cli.registry import register
from cryosaur.utils.errors import CryosaurError, handle_errors
from cryosaur.utils.io import _resolve_input_paths
from cryosaur.utils.log import log

# -- run_local: runs the pipeline for every resolved path, previewing or finalising each
def run_local(
    mrc_paths: list[Path],
    output_dir: Path,
    lowpass_radius: float,
    lowpass_sigma: float,
    lowpass_units: int,
    preview: bool,
) -> None:
    for mrc_path in mrc_paths:
        result = run_trim_pipeline(mrc_path, output_dir, lowpass_radius, lowpass_sigma, lowpass_units)

        if preview:
            preview_path = output_dir / f'{mrc_path.stem}_preview.png'
            build_preview(
                {
                    'Original': result.source,
                    'Filtered': result.filtered_for_surface,
                    'Flattened': result.flattened,
                    'Trimmed': result.trimmed,
                },
                preview_path,
            )
            log.info(f'  <cyan>{mrc_path.name}</cyan> -> preview at {preview_path}')
            continue

        final_path = output_dir / f'{mrc_path.stem}_trimmed.mrc'
        result.trimmed.rename(final_path)
        for intermediate in (
            result.filtered_for_surface,
            result.surface_model,
            result.warp_file,
            result.flattened,
            result.filtered_for_pitch,
            result.pitch_model,
        ):
            intermediate.unlink(missing_ok=True)
        log.info(f'  <cyan>{mrc_path.name}</cyan> -> {final_path}')

@register('trim-vol')
@handle_errors
def trim_command(
    input_path: Annotated[
        Path,
        typer.Argument(help='A single reconstructed tomogram MRC file, or a directory of these.'),
    ],
    lowpass_radius: Annotated[
        float,
        typer.Option('--lowpass-radius', help='mtffilter -lowpass radius: cutoff for the high-frequency roll-off used only to help findsection see through ice.'),
    ] = 0.0,
    lowpass_sigma: Annotated[
        float,
        typer.Option('--lowpass-sigma', help='mtffilter -lowpass sigma: roll-off width for the same filter.'),
    ] = 0.05,
    lowpass_units: Annotated[
        int,
        typer.Option('--lowpass-units', help='mtffilter -units: 1/2 for radius+sigma in nm/A, -1/-2 for 1/nm or 1/A, 3/4/-3/-4 to enter as sigma values instead.'),
    ] = 2,
    cluster: Annotated[
        str | None,
        typer.Option('--cluster', help='Submit via the named scheduler backend (e.g. slurm) instead of running locally.'),
    ] = None,
    preview: Annotated[
        bool,
        typer.Option('--preview', help='Run the pipeline into scratch and produce a stitched comparison image.'),
    ] = False,
    output_dir: Annotated[
        Path | None,
        typer.Option('--output-dir', help='Path to directory to write trimmed output(s) to (derived from the input path if omitted).'),
    ] = None,
) -> None:
    '''
    Automatically trim tomogram volumes using IMOD.
    '''
    mrc_paths = _resolve_input_paths(input_path, 'mrc')
    resolved_output_dir = output_dir or input_path.parent
    log.info(f'trim-vol: {len(mrc_paths)} file(s) to process')

    if cluster is not None:
        for mrc_path in mrc_paths:
            script_path = build_submission_script(mrc_path, resolved_output_dir, lowpass_radius, lowpass_sigma, lowpass_units, cluster)
            submit_job(script_path, cluster)
        return

    confirm_local_run('trim-vol')
    run_local(mrc_paths, resolved_output_dir, lowpass_radius, lowpass_sigma, lowpass_units, preview)