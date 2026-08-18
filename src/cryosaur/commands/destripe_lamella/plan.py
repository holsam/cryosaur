'''
CRYOSAUR: destrip-lamella plan builder logic
'''

# -- Import external dependencies
from datetime import datetime, timezone
from pathlib import Path

# -- Import cryosaur utilities
from cryosaur.commands.destripe_lamella.bridge import build_bridging_star, parse_tilt_series_star_loop
from cryosaur.utils.relion_adapter.job_star import extract_relion_headers, read_job_options, write_job_star
from cryosaur.utils.relion_adapter.lineage import build_lineage, write_lineage
from cryosaur.utils.relion_adapter.pipeline_graph import PipelineGraph
from cryosaur.utils.relion_adapter.plan import BridgingContract, PlannedStep, RunPlan, SlurmResourceProfile
from cryosaur.utils.relion_adapter.rerun import STEP_JOB_TYPES

# -- Map step name to job type for reruns
STEP_JOB_TYPES['reconstruct'] = 'relion.reconstructtomograms'
STEP_JOB_TYPES['denoise'] = 'relion.denoisetomo'
STEP_JOB_TYPES['segment'] = 'membrain.segment'

_BASELINE_RESOURCES = SlurmResourceProfile(
    partition='cs05r',
    gpus=4,
    ntasks=1,
    cpus_per_task=40,
    mem_per_gpu='32000M',
    time='72:00:00',
    modules=[
        'cuda/12.2',
        'EM/AreTomo2/2024-09-05',
        'EM/cryocare/0.3.0',
        'EM/ctffind/4.1.14-rhel8',
        'EM/Gctf/1.18',
        'EM/icebreaker/0.3.5',
        'EM/membrain-seg',
        'EM/MotionCor2/1.6.3',
        'EM/relion/5.0/2024-12-09',
        'EM/topaz',
        'fftw/3.3.8',
        'gcc/11.2.0',
        'hwloc/2.10.0',
        'openmpi/4.1.2',
    ],
)

_RESOLVE_TOKEN = '{{{{resolve:{job_type}}}}}'

# -- Define constants for PyLisC
_FILENAME_TEMPLATE = '{}_{position}_{}_{tilt}_{}_{}_{}_{}_{}.mrc'
_PYLISC_SUFFIX = '_PyLisC_angular'  # hardcoded by pylisc
_DESTRIPE_SUFFIX = '_destriped'      # cryosaur's own preferred naming, applied by a rename step below

# -- _destripe_commands: runs pylisc over the whole input directory in one call, then renames every output file (.mrc and any accompanying files, e.g. .log) from pylisc's hardcoded _PyLisC_angular suffix to cryosaur's own _destriped suffix
def _destripe_commands(input_dir: Path, output_dir: Path) -> list[str]:
    pylisc_command = (
        f'pylisc frames --workers {8} --output-dir {output_dir} '
        f"--filename-template '{_FILENAME_TEMPLATE}' {input_dir}"
    )
    rename_command = (
        f'shopt -s nullglob; for f in {output_dir}/*{_PYLISC_SUFFIX}.*; do '
        f'mv "$f" "${{f/{_PYLISC_SUFFIX}/{_DESTRIPE_SUFFIX}}}"; done'
    )
    return [pylisc_command, rename_command]

# -- _stage_relion_job: writes a job.star to fork_dir/cryosaur/staged/, returning the commands that resolve and then run it
def _stage_relion_job(
    fork_dir: Path, step_name: str, relion_job_type: str, options: dict[str, str], *, is_tomo: bool
) -> list[str]:
    staged_path = fork_dir / 'cryosaur' / 'staged' / f'{step_name}.star'
    write_job_star(relion_job_type, options, staged_path, is_tomo=is_tomo)
    return [
        f'cd {fork_dir} && [ -f default_pipeline.star ] || pipeliner --new_project',
        f'cryosaur resolve-star-path --fork-dir {fork_dir} --job-star {staged_path}',
        f'cd {fork_dir} && pipeliner --run_job {staged_path.relative_to(fork_dir)}',
    ]

# -- _read_source_alignment: returns the source project's tomogram list and the (tomo_name, micrograph_path) pairs its per-tilt STAR files reference
def _read_source_alignment(
    source_project: Path, aligned_tilt_series: Path
) -> tuple[list[str], list[tuple[str, str]]]:
    top_columns, top_rows = parse_tilt_series_star_loop(aligned_tilt_series)
    name_column = top_columns.index('rlnTomoName')
    star_file_column = top_columns.index('rlnTomoTiltSeriesStarFile')

    tomogram_names: list[str] = []
    micrograph_pairs: list[tuple[str, str]] = []
    for row in top_rows:
        tomo_name = row[name_column]
        tomogram_names.append(tomo_name)
        columns, rows = parse_tilt_series_star_loop(source_project / row[star_file_column])
        micrograph_column = columns.index('rlnMicrographName')
        for tilt_row in rows:
            micrograph_pairs.append((tomo_name, tilt_row[micrograph_column]))

    return tomogram_names, micrograph_pairs

# -- build_plan: reads source_project, plans a destripe-lamella branch into fork_dir, and returns the RunPlan
def build_plan(source_project: Path, fork_dir: Path) -> RunPlan:
    graph = PipelineGraph.from_star(source_project)
    headers = extract_relion_headers(source_project / 'default_pipeline.star')

    align_jobs = graph.jobs_of_type('relion.aligntiltseries.aretomo')
    if not align_jobs:
        raise ValueError(f'No relion.aligntiltseries.aretomo job found in {source_project}')
    align_job = align_jobs[-1]

    lineage = build_lineage(source_project, graph, align_job.name)
    write_lineage(lineage, fork_dir)

    aligned_tilt_series = source_project / align_job.name / 'aligned_tilt_series.star'
    tomogram_names, micrograph_pairs = _read_source_alignment(source_project, aligned_tilt_series)

    # -- destripe: cryosaur's own external step, not a pipeliner job
    destripe_job_dir = fork_dir / 'PyLisC' / 'job001'
    destripe_output_dir = destripe_job_dir / 'destriped'

    # Assert the expected flat directory layout
    micrograph_dirs = {str(Path(path).parent) for _, path in micrograph_pairs}
    if len(micrograph_dirs) != 1:
        raise ValueError(
            f'Expected all source micrographs to share one parent directory for a single pylisc frames call, found {len(micrograph_dirs)}: {micrograph_dirs}'
        )
    destripe_input_dir = source_project / micrograph_dirs.pop()

    destriped_micrograph_for: dict[tuple[str, str], str] = {}
    for tomo_name, original_path in micrograph_pairs:
        new_path = destripe_output_dir / f'{Path(original_path).stem}{_DESTRIPE_SUFFIX}.mrc'
        destriped_micrograph_for[(tomo_name, original_path)] = str(new_path.relative_to(fork_dir))

    destripe_step = PlannedStep(
        name='destripe',
        kind='external',
        job_dir=destripe_job_dir,
        depends_on=[],
        array_over=None,  # pylisc frames processes the whole directory in one call
        commands=_destripe_commands(destripe_input_dir, destripe_output_dir),
        expected_outputs=[fork_dir / p for p in destriped_micrograph_for.values()],
        resources=_BASELINE_RESOURCES.model_copy(update={'gpus': 0, 'cpus_per_task': 8, 'mem_per_gpu': None, 'mem_per_cpu': '4000M'}),
    )

    # bridging STAR
    contract = BridgingContract()
    bridging_job_dir = fork_dir / 'cryosaur' / 'bridge'
    bridging_star = build_bridging_star(
        source_project=source_project,
        source_aligned_tilt_series=aligned_tilt_series,
        fork_dir=fork_dir,
        fork_job_dir=bridging_job_dir,
        destriped_micrograph_for=destriped_micrograph_for,
        contract=contract,
    )

    staged_dir = fork_dir / 'cryosaur' / 'staged'

    # -- reconstruct
    source_reconstruct = graph.jobs_of_type('relion.reconstructtomograms')[-1]
    reconstruct_options = read_job_options(source_project / source_reconstruct.name / 'job.star')
    reconstruct_options['in_tiltseries'] = str(bridging_star.relative_to(fork_dir))
    reconstruct_commands = _stage_relion_job(
        fork_dir, 'reconstruct', 'relion.reconstructtomograms', reconstruct_options, is_tomo=False
    )
    reconstruct_step = PlannedStep(
        name='reconstruct',
        kind='relion',
        job_dir=staged_dir,
        depends_on=['destripe'],
        commands=reconstruct_commands,
        expected_outputs=[],  # not knowable until pipeliner runs it - see rerun.py
        resources=_BASELINE_RESOURCES.model_copy(update={'gpus': 0, 'mem_per_gpu': None, 'mem': '16G'}),
    )

    # -- denoise
    source_denoise = graph.jobs_of_type('relion.denoisetomo')[-1]
    denoise_options = read_job_options(source_project / source_denoise.name / 'job.star')
    denoise_options['in_tomoset'] = _RESOLVE_TOKEN.format(job_type='relion.reconstructtomograms')
    denoise_commands = _stage_relion_job(
        fork_dir, 'denoise', 'relion.denoisetomo', denoise_options, is_tomo=True
    )
    denoise_step = PlannedStep(
        name='denoise',
        kind='relion',
        job_dir=staged_dir,
        depends_on=['reconstruct'],
        commands=denoise_commands,
        expected_outputs=[],
        resources=_BASELINE_RESOURCES.model_copy(update={'gpus': 1, 'mem_per_gpu': None, 'mem': '16G'}),
    )

    # -- segment
    source_segment = graph.jobs_of_type('membrain.segment')[-1]
    segment_options = read_job_options(source_project / source_segment.name / 'job.star')
    segment_options['in_tomoset'] = _RESOLVE_TOKEN.format(job_type='relion.denoisetomo')
    segment_commands = _stage_relion_job(
        fork_dir, 'segment', 'membrain.segment', segment_options, is_tomo=True
    )
    segment_step = PlannedStep(
        name='segment',
        kind='relion',
        job_dir=staged_dir,
        depends_on=['denoise'],
        commands=segment_commands,
        expected_outputs=[],
        resources=_BASELINE_RESOURCES.model_copy(update={'gpus': 1, 'mem_per_gpu': None, 'mem': '16G'}),
    )

    return RunPlan(
        source_project=source_project,
        source_read_at=datetime.now(timezone.utc),
        source_relion_version=headers.relion_version,
        source_pipeliner_version=headers.pipeliner_version,
        fork_dir=fork_dir,
        branch_point=align_job.name,
        bridging_contract=contract,
        cryosaur_version='0.1.0',
        steps=[destripe_step, reconstruct_step, denoise_step, segment_step],
    )
