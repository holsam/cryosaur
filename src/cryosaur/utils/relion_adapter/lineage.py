'''
CRYOSAUR: record of previous jobs a branch depends on
'''

# -- Import external dependencies
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel

# -- Import cryosaur utilities
from cryosaur.utils.relion_adapter.job_star import read_job_options
from cryosaur.utils.relion_adapter.pipeline_graph import PipelineGraph

# -- LineageJob: one ancestor job a branch depends on, and the options it ran with
class LineageJob(BaseModel):
    name: str
    job_type: str
    options: dict[str, str]

# -- Lineage: the full ancestor record for a branch
class Lineage(BaseModel):
    source_project: Path
    branch_point: str
    recorded_at: datetime
    jobs: list[LineageJob]

# -- _ancestors: recursively collects job_name and everything transitively upstream of it into seen, in place
def _ancestors(graph: PipelineGraph, job_name: str, seen: set[str]) -> None:
    if job_name in seen:
        return
    seen.add(job_name)
    for upstream_job in graph.upstream(job_name):
        _ancestors(graph, upstream_job.name, seen)

# -- build_lineage: walks the ancestor subgraph of branch_point and records each job's options
def build_lineage(source_project: Path, graph: PipelineGraph, branch_point: str) -> Lineage:
    ancestor_names: set[str] = set()
    _ancestors(graph, branch_point, ancestor_names)

    jobs = [
        LineageJob(
            name=job.name,
            job_type=job.job_type,
            options=read_job_options(source_project / job.name / 'job.star'),
        )
        for job in graph.all_jobs()
        if job.name in ancestor_names
    ]
    return Lineage(
        source_project=source_project,
        branch_point=branch_point,
        recorded_at=datetime.now(),
        jobs=jobs,
    )


# -- write_lineage: writes a Lineage to <fork_dir>/cryosaur/lineage.json
def write_lineage(lineage: Lineage, fork_dir: Path) -> Path:
    path = fork_dir / 'cryosaur' / 'lineage.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(lineage.model_dump_json(indent=2))
    return path
