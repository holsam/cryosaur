'''
CRYOSAUR: resolution of a staged job.star's templated paths
'''

# -- Import external dependencies
import re, typer
from pathlib import Path
from typing import Annotated

# -- Import cryosaur utilities
from cryosaur.utils.errors import CryosaurError
from cryosaur.utils.log import log
from cryosaur.utils.cli.registry import register
from cryosaur.utils.relion_adapter.pipeline_graph import PipelineGraph

# -- _TOKEN_RE: regex pattern indicating paths to replace
_TOKEN_RE = re.compile(r'\{\{resolve:([^}]+)\}\}')

# -- UnresolvedTokenError: raised when a token's referenced job type has no completed job yet
class UnresolvedTokenError(CryosaurError):
    pass

# -- resolve_star_path: replaces every {{resolve:<job_type>}} token in job_star_path with that job type's output path in fork_dir's own pipeline.star
def resolve_star_path(fork_dir: Path, job_star_path: Path) -> None:
    graph = PipelineGraph.from_star(fork_dir)
    text = job_star_path.read_text()

    def _replace(match: re.Match) -> str:
        job_type = match.group(1)
        node = graph.latest_output(job_type)
        if node is None:
            raise UnresolvedTokenError(f'No completed {job_type} job found in {fork_dir}')
        return node.name

    resolved = _TOKEN_RE.sub(_replace, text)
    job_star_path.write_text(resolved)
    log.info(f'Resolved templated paths in <cyan>{job_star_path}</cyan>')


# -- resolve_star_path_command: CLI entry point under utils command
@register('resolve-star-paths', group='internal')
def resolve_star_path_command(
    fork_dir: Annotated[Path, typer.Option('--fork-dir', help='The fork project directory.')],
    job_star: Annotated[Path, typer.Option('--job-star', help='The staged job.star to resolve in place.')],
) -> None:
    '''
    Resolve and replace upstream paths in a staged job.star file.
    '''
    resolve_star_path(fork_dir, job_star)