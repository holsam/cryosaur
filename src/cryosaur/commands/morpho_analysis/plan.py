'''
CRYOSAUR: morpho-analysis command plan builder
'''

# -- Import external dependencies
from pathlib import Path

# -- build_commands: label -> model -> analyse evaluator chain, run sequentially in one submission script
def build_commands(segmentation_dir: Path, output_dir: Path, jobs: int) -> list[str]:
    label_dir = output_dir / 'evaluator/label'
    return [
        f'evaluator label {segmentation_dir} -o {output_dir} -j {jobs}',
        f'evaluator model {label_dir} -o {output_dir} -j {jobs}',
        f'evaluator analyse {label_dir} -o {output_dir} -j {jobs}',
    ]
