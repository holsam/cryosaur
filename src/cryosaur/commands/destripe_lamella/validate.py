'''
CRYOSAUR: destripe-lamella command validation
'''

# -- Import cryosaur utilities
from cryosaur.utils.relion_adapter.plan import RunPlan

# -- validate: returns a list of problems with a destripe-lamella RunPlan, checked both when the plan is built and again immediately before submission
def validate(plan: RunPlan) -> list[str]:
    problems: list[str] = []

    if not plan.source_project.exists():
        problems.append(f'Source project no longer exists at {plan.source_project}')

    destripe_step = plan.step('destripe')
    if not destripe_step.array_over:
        problems.append('destripe step has no tomograms to process - array_over is empty')

    staged_dir = plan.fork_dir / 'cryosaur' / 'staged'
    for step in plan.steps:
        if step.kind == 'relion':
            staged_path = staged_dir / f'{step.name}.star'
            if not staged_path.exists():
                problems.append(f"{step.name}: staged job.star not found at {staged_path}")

    if not plan.fork_dir.exists():
        problems.append(f'Fork directory does not exist: {plan.fork_dir}')

    return problems