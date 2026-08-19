'''
CRYOSAUR: reading and writing RELION5 job.star files
'''

# -- Import external dependencies
import re
from pathlib import Path
from pydantic import BaseModel

# -- Import cryosaur utilities
from cryosaur.utils.log import log

# -- Define constant for regex patterns
_VERSION_RE = re.compile(r'#\s*version\s+(\S+)')
_PIPELINER_RE = re.compile(r'#\s*CCP-EM Pipeliner version\s+(\S+)')

# -- RelionHeaders: the RELION and CCP-EM Pipeliner versions a STAR file was written by
class RelionHeaders(BaseModel):
    relion_version: str
    pipeliner_version: str

# -- extract_relion_headers: returns the RELION/Pipeliner version comments from a STAR file's header
def extract_relion_headers(path: Path) -> RelionHeaders:
    text = path.read_text()
    version_match = _VERSION_RE.search(text)
    pipeliner_match = _PIPELINER_RE.search(text)
    if not version_match or not pipeliner_match:
        log.error(f'Could not find RELION/Pipeliner version headers in {path}')
        raise ValueError(f'Could not find RELION/Pipeliner version headers in {path}')
    return RelionHeaders(
        relion_version=version_match.group(1),
        pipeliner_version=pipeliner_match.group(1),
    )

# -- read_job_options: reads an existing job.star's data_joboptions_values loop into a plain dict
def read_job_options(job_star_path: Path) -> dict[str, str]:
    import starfile

    tables = starfile.read(job_star_path, always_dict=True)
    options = tables['joboptions_values']
    return dict(zip(options['rlnJobOptionVariable'], options['rlnJobOptionValue']))

# -- render_job_star: returns job.star text for a new job, in the same block shape as a real export
def render_job_star(
    relion_job_type: str,
    resolved_options: dict[str, str],
    *,
    is_continue: bool = False,
    is_tomo: bool,
) -> str:
    lines = [
        '',
        '# version 50001',
        '# CCP-EM Pipeliner version 1.5.0',
        '',
        'data_job',
        '',
        f'_rlnJobTypeLabel    {relion_job_type}',
        ' ',
        f'_rlnJobIsContinue    {int(is_continue)}',
        ' ',
        f'_rlnJobIsTomo    {int(is_tomo)}',
        ' ',
        '',
        '# version 50001',
        '# CCP-EM Pipeliner version 1.5.0',
        '',
        'data_joboptions_values',
        '',
        'loop_ ',
        '_rlnJobOptionVariable #1 ',
        '_rlnJobOptionValue #2 ',
    ]
    for variable, value in sorted(resolved_options.items()):
        lines.append(f'{variable} {value} ')
    lines.append(' ')
    lines.append('')
    return '\n'.join(lines)

# -- write_job_star: writes render_job_star's output to output_path
def write_job_star(
    relion_job_type: str,
    resolved_options: dict[str, str],
    output_path: Path,
    *,
    is_continue: bool = False,
    is_tomo: bool,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        render_job_star(
            relion_job_type, resolved_options, is_continue=is_continue, is_tomo=is_tomo
        )
    )
