'''
CRYOSAUR: run plan serialisation
'''

# -- Import external dependencies
from pathlib import Path

# -- Import cryosaur utilities
from cryosaur.utils.errors import CryosaurError
from cryosaur.utils.log import log
from cryosaur.utils.relion_adapter.plan import RunPlan

PLAN_FILENAME = 'cryosaur_plan.json'

# -- plan_path: returns the path a fork's plan.json is read from and written to
def plan_path(fork_dir: Path) -> Path:
    return fork_dir / PLAN_FILENAME

# -- write_plan: writes plan to <fork_dir>/cryosaur/plan.json, always, whether or not submission follows
def write_plan(plan: RunPlan) -> Path:
    path = plan_path(plan.fork_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(plan.model_dump_json(indent=2))
    log.debug(f'Wrote plan to <cyan>{path}</cyan>')
    return path

# -- read_plan: reads a previously written plan back from a fork directory, for --from/--only re-runs
def read_plan(fork_dir: Path) -> RunPlan:
    path = plan_path(fork_dir)
    if not path.exists():
        log.error(f'No plan found at <cyan>{path}</cyan>')
        raise CryosaurError(f'No plan found at {path}')
    return RunPlan.model_validate_json(path.read_text())
