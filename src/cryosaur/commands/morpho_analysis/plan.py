'''
CRYOSAUR: morpho-analysis command plan builder
'''

# -- Import external dependencies
from pathlib import Path

# -- Import cryosaur utilities
from cryosaur.utils.cluster.base import ResourceProfile
from cryosaur.utils.relion_adapter.plan import PlannedStep

# -- build_steps: plans the label -> model -> analyse evaluator chain over a directory of segmentations
def build_steps(segmentation_dir: Path, output_dir: Path, jobs: int, resources: ResourceProfile) -> list[PlannedStep]:
    resources = resources.model_copy(update={'cpus_per_task': jobs})

    label_dir = output_dir / 'evaluator/label'
    model_dir = output_dir / 'evaluator/model'
    analyse_dir = output_dir / 'evaluator/analyse'

    label_step = PlannedStep(
        name='label',
        kind='external',
        job_dir=label_dir,
        commands=[f'evaluator label {segmentation_dir} -o {output_dir} -j {jobs}'],
        expected_outputs=[label_dir],
        resources=resources,
    )
    model_step = PlannedStep(
        name='model',
        kind='external',
        job_dir=model_dir,
        commands=[f'evaluator model {label_dir} -o {output_dir} -j {jobs}'],
        expected_outputs=[model_dir],
        resources=resources,
    )
    analyse_step = PlannedStep(
        name='analyse',
        kind='external',
        job_dir=analyse_dir,
        commands=[f'evaluator analyse {label_dir} -o {output_dir} -j {jobs}'],
        expected_outputs=[analyse_dir],
        resources=resources,
    )
    return [label_step, model_step, analyse_step]
