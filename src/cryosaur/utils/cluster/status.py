'''
CRYOSAUR: cluster status model
'''

# -- Import external dependencies
from dataclasses import dataclass
from typing import Optional

# -- ClusterStatus: dataclass holding cluster information
@dataclass
class ClusterStatus:
    recognised: bool
    scheduler: Optional[str] = None
    on_cluster: bool = False
    in_job: Optional[bool] = None
    message: Optional[str] = None
