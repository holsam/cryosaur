'''
CRYOSAUR: partial re-run resolution
'''

# -- Import cryosaur utilities
from cryosaur.utils.errors import CryosaurError
from cryosaur.utils.relion_adapter.pipeline_graph import JobStatus, PipelineGraph
from cryosaur.utils.relion_adapter.plan import PlannedStep, RunPlan

# Maps a PlannedStep name to a RELION job type its completion is checked against
STEP_JOB_TYPES: dict[str, str] = {}

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
    if not prerequisites:
        return

    graph: PipelineGraph | None = None
    for step in prerequisites:
        if step.name in STEP_JOB_TYPES:
            graph = graph or PipelineGraph.from_star(plan.fork_dir)
            job_type = STEP_JOB_TYPES[step.name]
            finished = [j for j in graph.jobs_of_type(job_type) if j.status == JobStatus.FINISHED]
            if not finished:
                raise MissingOutputsError(f'Step {step.name} is a prerequisite but no finished {job_type} job was found in {plan.fork_dir}')
        else:
            missing = [p for p in step.expected_outputs if not p.exists()]
            if missing:
                raise MissingOutputsError(f'Step {step.name} is a prerequisite but is missing expected output(s): {', '.join(str(p) for p in missing)}')

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
