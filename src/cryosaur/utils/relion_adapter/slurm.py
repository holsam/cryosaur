'''
CRYOSAUR: SLURM script rendering
'''

# -- Import external dependencies
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path

# -- Import cryosaur utilities
from cryosaur.utils.relion_adapter.plan import PlannedStep


_TEMPLATE_DIR = Path(__file__).parent / 'templates'
_env = Environment(
    loader=FileSystemLoader(_TEMPLATE_DIR),
    trim_blocks=True,
    lstrip_blocks=True,
    autoescape=select_autoescape(disabled_extensions=('j2',)),
)

# -- render_slurm_script: returns the SLURM submission script text for a single planned step
def render_slurm_script(step: PlannedStep) -> str:
    template = _env.get_template('step.sh.j2')
    return template.render(step=step, resources=step.resources)

# -- write_slurm_script: writes a step's rendered SLURM script into its job directory, returning the script path
def write_slurm_script(step: PlannedStep) -> Path:
    script_path = step.job_dir / f'{step.name}.sh'
    step.job_dir.mkdir(parents=True, exist_ok=True)
    script_path.write_text(render_slurm_script(step))
    return script_path
