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

    for step in plan.steps:
        if not step.commands:
            problems.append(f'{step.name}: no commands found for this step')
        if not step.expected_outputs:
            problems.append(f'{step.name}: no expected outputs found for this step')

    if not plan.fork_dir.exists():
        problems.append(f'Fork directory does not exist: {plan.fork_dir}')

    return problems
