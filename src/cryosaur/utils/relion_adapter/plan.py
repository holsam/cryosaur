'''
CRYOSAUR: models describing a planned branch (a "run plan") before submission
'''

# -- Import external dependencies
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Literal

# -- Import cryosaur utilities
from cryosaur.utils.errors import CryosaurError
from cryosaur.utils.slurm import SlurmResourceProfile

# -- BridgingContract: declares which parts of the source project's tilt series metadata a command's steps leave unchanged
class BridgingContract(BaseModel):
    preserves_pixel_size: bool = True
    preserves_tilt_count: bool = True
    preserves_tilt_order: bool = True
    preserves_alignment: bool = True
    preserves_ctf: bool = True
    preserves_dose: bool = True

# -- PlannedStep: one step of a branch, either a real RELION job or an external tool
class PlannedStep(BaseModel):
    name: str
    kind: Literal['relion', 'external']
    job_dir: Path
    depends_on: list[str] = Field(default_factory=list)
    array_over: list[str] | None = None
    commands: list[str]
    expected_outputs: list[Path] = Field(default_factory=list)
    resources: SlurmResourceProfile

# -- RunPlan: the full, serialisable description of a branch
class RunPlan(BaseModel):
    source_project: Path
    source_read_at: datetime
    source_relion_version: str
    source_pipeliner_version: str
    fork_dir: Path
    branch_point: str
    bridging_contract: BridgingContract
    cryosaur_version: str
    steps: list[PlannedStep]

    # -- step: returns the PlannedStep with the given name, raising if not found
    def step(self, name: str) -> PlannedStep:
        for step in self.steps:
            if step.name == name:
                return step
        raise CryosaurError(f'No step named {name!r} in this plan')

    # -- steps_from: returns the named step and everything after it, in the plan's original (submission) order
    def steps_from(self, name: str) -> list[PlannedStep]:
        self.step(name)  # raises if name doesn't exist
        started = False
        result = []
        for step in self.steps:
            if step.name == name:
                started = True
            if started:
                result.append(step)
        return result
