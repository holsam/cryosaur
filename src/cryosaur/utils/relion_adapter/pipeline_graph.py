'''
CRYOSAUR: read-only access to an existing RELION5 project's job graph
'''

# -- Import external dependencies
from enum import Enum
from pathlib import Path
from pydantic import BaseModel, Field

# -- Import cryosaur utilities
from cryosaur.utils.log import log

# -- JobStatus: class defining cryosaur job statuses, mapped from RELION's own status labels
class JobStatus(str, Enum):
    SCHEDULED = 'scheduled'
    RUNNING = 'running'
    FINISHED = 'finished'
    FAILED = 'failed'
    UNKNOWN = 'unknown'

_STATUS_MAP = {
    'Running': JobStatus.RUNNING,
    'Scheduled': JobStatus.SCHEDULED,
    'Succeeded': JobStatus.FINISHED,
    'Failed': JobStatus.FAILED,
}


# -- _status_from_relion: returns the JobStatus corresponding to one of RELION's own status labels
def _status_from_relion(label: str) -> JobStatus:
    return _STATUS_MAP.get(label, JobStatus.UNKNOWN)

# -- PipelineNode: a single RELION-tracked file
class PipelineNode(BaseModel):
    name: str
    node_type: str

# -- PipelineJob: a single RELION5 job
class PipelineJob(BaseModel):
    name: str
    job_type: str
    alias: str | None = None
    status: JobStatus
    input_nodes: list[PipelineNode] = Field(default_factory=list)
    output_nodes: list[PipelineNode] = Field(default_factory=list)

# -- PipelineGraph: in-memory graph built from a RELION5 project's default_pipeline.star
class PipelineGraph:
    def __init__(self, project_dir: Path, jobs: dict[str, PipelineJob]) -> None:
        self.project_dir = project_dir
        self._jobs = jobs

    # -- from_star: builds a PipelineGraph by parsing project_dir/star_name
    @classmethod
    def from_star(
        cls, project_dir: Path, star_name: str = 'default_pipeline.star'
    ) -> PipelineGraph:
        import starfile

        star_path = project_dir / star_name
        tables = starfile.read(star_path, always_dict=True)

        processes = tables['pipeline_processes']
        nodes = tables['pipeline_nodes']
        input_edges = tables['pipeline_input_edges']
        output_edges = tables['pipeline_output_edges']

        node_lookup = {
            row.rlnPipeLineNodeName: PipelineNode(
                name=row.rlnPipeLineNodeName, node_type=row.rlnPipeLineNodeTypeLabel
            )
            for row in nodes.itertuples()
        }

        jobs: dict[str, PipelineJob] = {}
        for row in processes.itertuples():
            alias = getattr(row, 'rlnPipeLineProcessAlias', 'None')
            if not hasattr(row, 'rlnPipeLineProcessAlias'):
                log.debug(f'{row.rlnPipeLineProcessName}: no rlnPipeLineProcessAlias column, defaulting to None')
            jobs[row.rlnPipeLineProcessName] = PipelineJob(
                name=row.rlnPipeLineProcessName,
                job_type=row.rlnPipeLineProcessTypeLabel,
                alias=None if alias == 'None' else alias,
                status=_status_from_relion(row.rlnPipeLineProcessStatusLabel),
            )
            log.debug(f'Parsed {len(jobs)} job(s) from {star_path}')

        for row in input_edges.itertuples():
            jobs[row.rlnPipeLineEdgeProcess].input_nodes.append(
                node_lookup[row.rlnPipeLineEdgeFromNode]
            )
        for row in output_edges.itertuples():
            jobs[row.rlnPipeLineEdgeProcess].output_nodes.append(
                node_lookup[row.rlnPipeLineEdgeToNode]
            )

        return cls(project_dir, jobs)

    # -- job: returns the PipelineJob with the given name
    def job(self, name: str) -> PipelineJob:
        return self._jobs[name]

    # -- all_jobs: returns every job in the graph
    def all_jobs(self) -> list[PipelineJob]:
        return list(self._jobs.values())

    # -- jobs_of_type: returns every job for the given job type
    def jobs_of_type(self, job_type: str) -> list[PipelineJob]:
        return [j for j in self._jobs.values() if j.job_type == job_type]

    # -- upstream: returns jobs whose output nodes feed this job's inputs
    def upstream(self, job_name: str) -> list[PipelineJob]:
        job = self._jobs[job_name]
        wanted = {n.name for n in job.input_nodes}
        return [j for j in self._jobs.values() if any(n.name in wanted for n in j.output_nodes)]

    # -- downstream: returns jobs that consume this job's outputs
    def downstream(self, job_name: str) -> list[PipelineJob]:
        job = self._jobs[job_name]
        wanted = {n.name for n in job.output_nodes}
        return [j for j in self._jobs.values() if any(n.name in wanted for n in j.input_nodes)]

    # -- latest_output: returns the most recent output node of a given job type, optionally filtered by node type
    def latest_output(self, job_type: str, node_type: str | None = None) -> PipelineNode | None:
        candidates = [
            n
            for j in self.jobs_of_type(job_type)
            for n in j.output_nodes
            if node_type is None or n.node_type == node_type
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda n: len(n.name))
