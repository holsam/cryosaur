'''
CRYOSAUR: partial re-run resolution
'''

# -- Import cryosaur utilities
from cryosaur.utils.errors import CryosaurError
from cryosaur.utils.log import log
from cryosaur.utils.relion_adapter.plan import PlannedStep, RunPlan

# -- MissingOutputsError: raised when a partial re-run's prerequisite steps haven't produced their expected outputs
class MissingOutputsError(CryosaurError):
    pass

# -- _check_prerequisite_outputs: raises MissingOutputsError if any step upstream of `steps` hasn't actually completed
def _check_prerequisite_outputs(plan: RunPlan, steps: list[PlannedStep]) -> None:
    submitting = {step.name for step in steps}
    prerequisites = [
        step
        for step in plan.steps
        if step.name not in submitting and any(step.name in s.depends_on for s in steps)
    ]
    for step in prerequisites:
        missing = [p for p in step.expected_outputs if not p.exists()]
        if missing:
            log.error(f'Step {step.name} is a prerequisite but is missing expected output(s): {", ".join(str(p) for p in missing)}')
            raise MissingOutputsError(f'Step {step.name} is a prerequisite but is missing expected output(s): {", ".join(str(p) for p in missing)}')
        else:
            log.debug(f'Prerequisite {step.name} satisfied ({len(step.expected_outputs)} expected output(s) present)')

# -- resolve_steps_to_submit: returns the steps a partial re-run should submit, given --from/--only, after checking prerequisites actually completed
def resolve_steps_to_submit(
    plan: RunPlan,
    *,
    from_step: str | None = None,
    only_step: str | None = None,
) -> list[PlannedStep]:
    if from_step and only_step:
        raise ValueError('--from and --only are mutually exclusive')
    if only_step:
        steps = [plan.step(only_step)]
    elif from_step:
        steps = plan.steps_from(from_step)
    else:
        steps = plan.steps
    _check_prerequisite_outputs(plan, steps)
    return steps
