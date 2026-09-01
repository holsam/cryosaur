'''
CRYOSAUR: `morpho-analysis` command CLI
'''

# -- Import external dependencies
import os, typer
from pathlib import Path
from rich.console import Console
from rich.table import Table
from typing import Annotated

# -- Import cryosaur utilities
from cryosaur.commands.morpho_analysis.collect import collect, make_symlinks, pair_files, summarise_counts
from cryosaur.commands.morpho_analysis.plan import build_commands
from cryosaur.utils.cli.options import ClusterResourcesOption
from cryosaur.utils.cli.registry import register
from cryosaur.utils.cluster.cluster import confirm_local_run, get_backend
from cryosaur.utils.config import load_config, resolve_resources
from cryosaur.utils.errors import CryosaurError, handle_errors
from cryosaur.utils.external.evaluator import run_evaluator_step
from cryosaur.utils.log import log

# -- JobsOption: number of workers passed as evaluator's -j (defaults to the resolved resources' cpus_per_task for --cluster, or os.cpu_count() locally)
JobsOption = Annotated[
    int | None,
    typer.Option('--jobs', '-j', help="Workers to pass as evaluator's -j (defaults to the cluster resources' cpus-per-task, or all local CPUs).", show_default=False, rich_help_panel='Pipeline Options'),
]

# -- _prompt_roots: interactively gathers root directories, one at a time, until a blank answer
def _prompt_roots() -> list[Path]:
    roots: list[Path] = []
    while True:
        answer = log.input('Root directory (leave blank to finish)', default='', show_default=False)
        if not answer:
            break
        root = Path(answer).expanduser().resolve()
        if not root.is_dir():
            log.error(f'Not a directory: {root}')
            continue
        roots.append(root)
    return roots

# -- _print_summary: prints a per-root/raw file count table (plus totals), returning its rows
def _print_summary(roots: list[Path]) -> list[tuple[str, str, int, int]]:
    rows = summarise_counts(roots)
    table = Table(title='Files found')
    table.add_column('Root')
    table.add_column('Raw')
    table.add_column('Tomograms', justify='right')
    table.add_column('Segmentations', justify='right')
    for root_name, raw_part, n_tomograms, n_segmentations in rows:
        table.add_row(root_name, raw_part, str(n_tomograms), str(n_segmentations))
    table.add_row('[bold]Total[/bold]', '', f'[bold]{sum(r[2] for r in rows)}[/bold]', f'[bold]{sum(r[3] for r in rows)}[/bold]')
    Console(stderr=True).print(table)
    return rows

# -- run_local: runs the label -> model -> analyse evaluator chain locally, in order
def run_local(segmentation_dir: Path, output_dir: Path, jobs: int) -> None:
    label_dir = run_evaluator_step('label', segmentation_dir, output_dir / 'Label' / 'job001', jobs)
    model_dir = run_evaluator_step('model', label_dir, output_dir / 'Model' / 'job002', jobs)
    run_evaluator_step('analyse', label_dir, output_dir / 'Analyse' / 'job003', jobs)
    log.info(f'  <cyan>label</cyan> -> {label_dir}')
    log.info(f'  <cyan>model</cyan> -> {model_dir}')
    log.info(f'  <cyan>analyse</cyan> -> {output_dir / "Analyse" / "job003"}')

@register('morpho-analysis', panel='Pipelines')
@handle_errors
def morpho_analysis_command(
    roots: Annotated[
        list[Path] | None,
        typer.Argument(help='One or more root directories to collect tomograms/segmentations from (prompted interactively if omitted).', show_default=False),
    ] = None,
    output_dir: Annotated[
        Path,
        typer.Option('--output-dir', '-o', help='Directory to symlink tomograms/segmentations into and run the evaluator label/model/analyse chain under.'),
    ] = Path('morph_analysis'),
    cluster: Annotated[
        str | None,
        typer.Option('--cluster', help='Submit via the named scheduler backend (e.g. slurm) instead of running locally.'),
    ] = None,
    cluster_resources: ClusterResourcesOption = None,
    jobs: JobsOption = None,
) -> None:
    '''
    Collect tomograms and segmentations then run EValuator's label/model/analyse commands over the collected segmentations.
    '''
    if not roots:
        roots = _prompt_roots()
    if not roots:
        raise CryosaurError('No root directories specified.')

    rows = _print_summary(roots)
    if not rows:
        raise CryosaurError(f'No .mrc tomograms/segmentations found under {", ".join(str(r) for r in roots)}')

    proceed = log.input('Proceed with these files', choices=['y', 'n'], default='n', case_sensitive=False)
    if proceed.lower() != 'y':
        log.info('Aborted.')
        raise typer.Exit(0)

    tomograms, segmentations = collect(roots)
    tomogram_dir = output_dir / 'tomograms'
    segmentation_dir = output_dir / 'segmentations'
    make_symlinks(tomograms, tomogram_dir)
    make_symlinks(segmentations, segmentation_dir)
    log.info(f'morpho-analysis: {len(pair_files(tomograms, segmentations))} matched tomogram/segmentation pair(s) collected')

    if cluster is not None:
        backend = get_backend(cluster.lower())
        if backend is None:
            raise CryosaurError(f'No {cluster!r} scheduler backend registered')
        resources = resolve_resources(load_config(), cluster_resources)
        n_jobs = jobs or resources.cpus_per_task
        resources = resources.model_copy(update={'name': 'cryosaur-morpho-analysis', 'cpus_per_task': n_jobs})
        commands = build_commands(segmentation_dir, output_dir, n_jobs)
        script_path = output_dir / 'morpho_analysis.sbatch'
        log_path = output_dir / 'morpho_analysis.log'
        backend.write_script(resources, commands, script_path, log_path)
        job_id = backend.submit(script_path)
        log.info(f'  <cyan>morpho-analysis</cyan> -> {cluster} job <cyan>{job_id}</cyan>')
        return

    confirm_local_run('morpho-analysis')
    run_local(segmentation_dir, output_dir, jobs or os.cpu_count() or 1)
