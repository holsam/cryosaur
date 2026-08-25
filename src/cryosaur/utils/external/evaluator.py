'''
CRYOSAUR: EValuator tool wrapper
'''

# -- Import external dependencies
import subprocess
from pathlib import Path

# -- Import cryosaur utilities
from cryosaur.utils.errors import CryosaurError
from cryosaur.utils.log import log

# -- run_evaluator_step: runs one EValuator subcommand (label/model/analyse) locally, writing results into output_dir
def run_evaluator_step(subcommand: str, input_dir: Path, output_dir: Path, jobs: int) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    command = ['evaluator', subcommand, str(input_dir), '-o', str(output_dir), '-j', str(jobs)]
    log.debug(f'Running {" ".join(command)}')
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        log.error(f'evaluator {subcommand} failed: {result.stderr.strip()}')
        raise CryosaurError(f'evaluator {subcommand} failed: {result.stderr.strip()}')
    return output_dir
