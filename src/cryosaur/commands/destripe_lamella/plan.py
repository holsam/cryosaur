'''
CRYOSAUR: destrip-lamella plan builder logic
'''

# -- Import external dependencies
from datetime import datetime, timezone
from importlib.metadata import version as _pkg_version
from pathlib import Path

# -- Import cryosaur utilities
from cryosaur.utils.config import load_config, resolve_resources
from cryosaur.utils.errors import CryosaurError
from cryosaur.utils.log import log
from cryosaur.utils.relion_adapter.job_star import extract_relion_headers
from cryosaur.utils.relion_adapter.lineage import build_lineage, write_lineage
from cryosaur.utils.relion_adapter.note_log import (
    NoteCommandError,
    extract_flag_value,
    find_command_for_tomogram,
    read_note_commands,
    substitute_paths,
)
from cryosaur.utils.relion_adapter.pipeline_graph import PipelineGraph
from cryosaur.utils.relion_adapter.plan import PlannedStep, RunPlan

# -- Define constants for PyLisC
_FILENAME_TEMPLATE = '{}_{position}_{}_{tilt}_{}_{}_{}_{}_{}.mrc'
_PYLISC_SUFFIX = '_PyLisC_angular'  # hardcoded by pylisc
_DESTRIPE_SUFFIX = '_destriped'      # cryosaur's own preferred naming, applied by a rename step below

# -- _tilt_angle: returns the tilt angle from a micrograph filename, used to order destriped images before stacking
def _tilt_angle(filename: str) -> float:
    token = Path(filename).stem.split('_')[3]
    try:
        return float(token)
    except ValueError:
        raise CryosaurError(f'Expected a numeric tilt angle at position 3 of {filename!r}, got {token!r}') from None

# -- _tomogram_prefix_match: returns True if filename belongs to tomo_name
def _tomogram_prefix_match(filename: str, tomo_name: str) -> bool:
    return filename.startswith(f'{tomo_name}_')

# -- _destripe_commands: runs pylisc over the whole input directory in one call, then renames every output file (.mrc and any accompanying files, e.g. .log) from pylisc's hardcoded _PyLisC_angular suffix to cryosaur's own _destriped
def _destripe_commands(input_dir: Path, output_dir: Path, *, workers: int) -> list[str]:
    pylisc_command = (
        f'pylisc frames --workers {workers} --output-dir {output_dir} '
        f"--filename-template '{_FILENAME_TEMPLATE}' {input_dir}"
    )
    rename_command = (
        f'shopt -s nullglob; for f in {output_dir}/*{_PYLISC_SUFFIX}.*; do '
        f'mv "$f" "${{f/{_PYLISC_SUFFIX}/{_DESTRIPE_SUFFIX}}}"; done'
    )
    return [pylisc_command, rename_command]

# -- _write_newstack_file_of_inputs: writes an IMOD "file of inputs" list for newstack -fileinlist
def _write_newstack_file_of_inputs(list_path: Path, ordered_paths: list[Path]) -> None:
    list_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [str(len(ordered_paths))]
    for path in ordered_paths:
        lines.append(str(path))
        lines.append('0')
    list_path.write_text('\n'.join(lines) + '\n')

# -- _stack_command: assembles one tomogram's destriped micrographs, in tilt-angle order (lowest negative to highest positive), into a single stack via newstack
def _stack_command(tomo_name: str, ordered_destriped_paths: list[Path], stack_dir: Path) -> str:
    list_path = stack_dir / f'{tomo_name}_inputs.txt'
    _write_newstack_file_of_inputs(list_path, ordered_destriped_paths)
    output_path = stack_dir / f'{tomo_name}_stack.mrc'
    return f'newstack -fileinlist {list_path} -output {output_path}'

# -- _reconstruct_commands: adapts the source project's AreTomo3 note.txt command for this tomogram to the fork's paths, switching -Cmd 1 (recompute) vs -Cmd 2 (reuse existing alignment) per reuse_alignment
def _reconstruct_commands(
    *,
    note_line: str,
    tomo_name: str,
    new_stack_path: Path,
    new_outdir: Path,
    reuse_alignment: bool,
    source_stack_dir: Path,
) -> list[str]:
    old_stack_path = extract_flag_value(note_line, '-InPrefix')
    old_outdir = extract_flag_value(note_line, '-OutDir')
    command = substitute_paths(note_line, [(old_stack_path, str(new_stack_path)), (old_outdir, str(new_outdir))])

    if not reuse_alignment:
        return [command]

    # -Cmd 2 needs the source project's .aln and _TLT.txt copied alongside the new destriped stack, matched by filename stem
    stem = f'{tomo_name}_stack'
    copy_commands = [
        f'cp {source_stack_dir / f"{stem}.aln"} {new_stack_path.parent / f"{stem}.aln"}',
        f'cp {source_stack_dir / f"{stem}_TLT.txt"} {new_stack_path.parent / f"{stem}_TLT.txt"}',
    ]
    reconstruct_command = command.replace('-Cmd 1', '-Cmd 2')
    return copy_commands + [reconstruct_command]

# -- _denoise_commands: adapts the source project's topaz note.txt line to the fork's paths
def _denoise_commands(note_line: str, new_input: Path, new_outdir: Path) -> list[str]:
    parts = note_line.split()
    old_input = parts[2]  # positional: topaz denoise3d <input> ...
    old_outdir = extract_flag_value(note_line, '-o')
    command = substitute_paths(note_line, [(old_input, str(new_input)), (old_outdir, str(new_outdir))])
    return [command]

# -- _segment_commands: adapts the source project's membrain note.txt line to the fork's paths
def _segment_commands(note_line: str, new_input: Path, new_outdir: Path) -> list[str]:
    old_input = extract_flag_value(note_line, '--tomogram-path')
    old_outdir = extract_flag_value(note_line, '--out-folder')
    command = substitute_paths(note_line, [(old_input, str(new_input)), (old_outdir, str(new_outdir))])
    return [command]

# -- build_plan: reads source_project, plans a destripe-lamella branch into fork_dir, and returns the RunPlan
def build_plan(source_project: Path, fork_dir: Path, *, reuse_alignment: bool = True, cluster_resources: str | None = None) -> RunPlan:
    log.info(f'Building plan from source project <cyan>{source_project}</cyan>')
    baseline_resources = resolve_resources(load_config(), cluster_resources)
    graph = PipelineGraph.from_star(source_project)
    headers = extract_relion_headers(source_project / 'default_pipeline.star')

    def _last_job(graph, job_type, source_project):
        jobs = graph.jobs_of_type(job_type)
        if not jobs:
            log.error(f'No {job_type} job found in {source_project}')
            raise CryosaurError(f'No {job_type} job found in {source_project}')
        return jobs[-1]

    exclude_tilts = _last_job(graph, 'relion.excludetilts', source_project)
    source_reconstruct = _last_job(graph, 'relion.reconstructtomograms', source_project)
    source_denoise = _last_job(graph, 'relion.denoisetomo', source_project)
    source_segment = _last_job(graph, 'membrain.segment', source_project)

    lineage = build_lineage(source_project, graph, source_reconstruct.name)
    write_lineage(lineage, fork_dir)

    # Read source_project's note.txt
    reconstruct_notes = read_note_commands(source_project / source_reconstruct.name / 'note.txt')
    denoise_notes = read_note_commands(source_project / source_denoise.name / 'note.txt')
    segment_notes = read_note_commands(source_project / source_segment.name / 'note.txt')

    # Read tomogram names from reconstruct_notes
    tomogram_names = sorted(
        {Path(extract_flag_value(line, '-InPrefix')).stem.removesuffix('_stack') for line in reconstruct_notes}, key=lambda n: int(n.removeprefix('Position_')),
    )

    # Define job directories
    destripe_job_dir = fork_dir / 'PyLisC' / 'job001'
    destripe_output_dir = destripe_job_dir / 'destriped'
    stack_dir = fork_dir / 'Stack' / 'job002'
    reconstruct_dir = fork_dir / 'Tomograms' / 'job003'
    denoise_dir = fork_dir / 'Denoise' / 'job004'
    segment_dir = fork_dir / 'Segmentation' / 'job005'

    # Group micrographs by tomogram, sorted into tilt-angle order (lowest negative to highest positive), for destripe's expected_outputs and stack's input lists
    destripe_input_dir = source_project / exclude_tilts.name / 'tilts'
    micrographs_by_tomogram: dict[str, list[Path]] = {name: [] for name in tomogram_names}
    for micrograph in sorted(destripe_input_dir.glob('*.mrc')):
        for name in tomogram_names:
            if _tomogram_prefix_match(micrograph.name, name):
                micrographs_by_tomogram[name].append(micrograph)
                break
    for name in tomogram_names:
        micrographs_by_tomogram[name].sort(key=lambda p: _tilt_angle(p.name))
    log.progress(f'Mapped {sum(len(value) for value in micrographs_by_tomogram.values())} micrograph(s) to {len(micrographs_by_tomogram.keys())} tomogram(s)')

    def _destriped_path(micrograph: Path) -> Path:
        return destripe_output_dir / f'{micrograph.stem}{_DESTRIPE_SUFFIX}.mrc'

    # -- destripe step
    destripe_resources = baseline_resources.model_copy(update={'gpus': 0, 'cpus_per_task': 12, 'mem_per_gpu': None, 'mem_per_cpu': '4G'})
    destripe_step = PlannedStep(
        name='destripe',
        kind='external',
        job_dir=destripe_job_dir,
        depends_on=[],
        array_over=None,  # pylisc frames processes the whole directory in one call
        commands=_destripe_commands(destripe_input_dir, destripe_output_dir, workers=destripe_resources.cpus_per_task),
        expected_outputs=[_destriped_path(m) for micrographs in micrographs_by_tomogram.values() for m in micrographs],
        resources=destripe_resources,
    )

    # -- stack step
    stack_commands: list[str] = []
    stack_outputs: list[Path] = []
    for name in tomogram_names:
        ordered_destriped = [_destriped_path(m) for m in micrographs_by_tomogram[name]]
        stack_commands.append(_stack_command(name, ordered_destriped, stack_dir))
        stack_outputs.append(stack_dir / f'{name}_stack.mrc')
    stack_step = PlannedStep(
        name='stack',
        kind='external',
        job_dir=stack_dir,
        array_over=None,  # process all in one script
        depends_on=['destripe'],
        commands=stack_commands,
        expected_outputs=stack_outputs,
        resources=baseline_resources.model_copy(update={'gpus': 0, 'cpus_per_task': 12, 'mem_per_gpu': None, 'mem_per_cpu': '4G'})
    )

    # -- reconstruct step
    source_reconstruct_stack_dir = source_project / source_reconstruct.name / 'tomograms'
    reconstruct_commands: list[str] = []
    reconstruct_outputs: list[Path] = []
    for name in tomogram_names:
        note_line = find_command_for_tomogram(reconstruct_notes, name)
        reconstruct_commands.extend(
            _reconstruct_commands(
                note_line=note_line,
                tomo_name=name,
                new_stack_path=stack_dir / f'{name}_stack.mrc',
                new_outdir=reconstruct_dir,
                reuse_alignment=reuse_alignment,
                source_stack_dir=source_reconstruct_stack_dir,
            )
        )
        reconstruct_outputs.append(reconstruct_dir / f'{name}_stack_Vol.mrc')
    reconstruct_step = PlannedStep(
        name='reconstruct',
        kind='external',
        job_dir=reconstruct_dir,
        array_over=None,  # process all in one script
        depends_on=['stack'],
        commands=reconstruct_commands,
        expected_outputs=reconstruct_outputs,
        resources=baseline_resources.model_copy(),
    )

    # -- denoise: topaz, one note.txt-derived command per tomogram
    denoise_commands: list[str] = []
    denoise_outputs: list[Path] = []
    for name, reconstruct_output in zip(tomogram_names, reconstruct_outputs):
        note_line = find_command_for_tomogram(denoise_notes, name)
        denoise_commands.extend(_denoise_commands(note_line, new_input=reconstruct_output, new_outdir=denoise_dir))
        denoise_outputs.append(denoise_dir / f'{reconstruct_output.stem}.denoised.mrc')
    denoise_step = PlannedStep(
        name='denoise',
        kind='external',
        job_dir=denoise_dir,
        array_over=None,  # process all in one script
        depends_on=['reconstruct'],
        commands=denoise_commands,
        expected_outputs=denoise_outputs,
        resources=baseline_resources.model_copy(),
    )

    # -- segment: membrain, one note.txt-derived command per tomogram
    segment_commands: list[str] = []
    segment_outputs: list[Path] = []
    for name, denoise_output in zip(tomogram_names, denoise_outputs):
        note_line = find_command_for_tomogram(segment_notes, name)
        segment_commands.extend(_segment_commands(note_line, new_input=denoise_output, new_outdir=segment_dir))
        segment_outputs.append(segment_dir / f'{denoise_output.stem}_segmented.mrc')
    segment_step = PlannedStep(
        name='segment',
        kind='external',
        job_dir=segment_dir,
        depends_on=['denoise'],
        commands=segment_commands,
        expected_outputs=segment_outputs,
        resources=baseline_resources.model_copy(),
    )

    plan = RunPlan(
        source_project=source_project,
        source_read_at=datetime.now(timezone.utc),
        source_relion_version=headers.relion_version,
        source_pipeliner_version=headers.pipeliner_version,
        fork_dir=fork_dir,
        branch_point=source_reconstruct.name,
        cryosaur_version=_pkg_version('cryosaur'),
        steps=[destripe_step, stack_step, reconstruct_step, denoise_step, segment_step],
    )
    log.info(f'Built plan with {len(plan.steps)} step(s): {", ".join(s.name for s in plan.steps)}')
    return plan
