import threading
import itertools
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class Position:
    ra: float
    dec: float

@dataclass
class Target:
    tid: int               # astronomer-assigned ID (unique per proposal)
    coordinates: Position
    exp_time: int          # seconds

@dataclass
class Observation:
    oid: int               # auto-incremented
    target_tid: int        # astronomer-assigned tid
    data_url: str
    remarks: Optional[str] = None

@dataclass
class Proposal:
    pid: int               # auto-incremented
    status: int            # 0=queued, 1=running, 2=ready
    targets: List[Target]  = field(default_factory=list)
    observations: List[Observation] = field(default_factory=list)

class InMemoryDB:
    def __init__(self):
        self._pid_gen = itertools.count(1)
        self._oid_gen = itertools.count(1)
        self._proposals: Dict[int, Proposal] = {}

        self._lock = threading.Lock()

    def store_proposal(self, targets: List[Target]) -> int:
        """Assign a new pid, store the list of Targets, return pid."""
        with self._lock:
            pid = next(self._pid_gen)
            prop = Proposal(pid=pid, status=0, targets=list(targets))
            # ensure uniqueness of tid within this proposal
            tids = [t.tid for t in targets]
            if len(tids) != len(set(tids)):
                raise ValueError("Target IDs (tid) must be unique per proposal")
            self._proposals[pid] = prop
            return pid

    def get_status(self, pid: int) -> int:
        """Return status for proposal pid, or KeyError if missing."""
        with self._lock:
            return self._proposals[pid].status

    def get_proposal(self, pid: int) -> Proposal:
        """Return full Proposal object (deep copy if you want safety)."""
        with self._lock:
            return self._proposals[pid]

    def list_proposals(self) -> List[Proposal]:
        """Return all stored proposals."""
        with self._lock:
            return list(self._proposals.values())

    def update_status(self, pid: int, new_status: int) -> None:
        """Set status = new_status (0,1,2)."""
        with self._lock:
            self._proposals[pid].status = new_status

    def insert_observation(
        self, pid: int, target_tid: int, data_url: str, remarks: str = None
    ) -> int:
        """Add an Observation to a given proposal and target, return oid."""
        with self._lock:
            prop = self._proposals[pid]
            # check target exists
            if target_tid not in {t.tid for t in prop.targets}:
                raise KeyError(f"Target {target_tid} not in proposal {pid}")
            oid = next(self._oid_gen)
            obs = Observation(oid=oid, target_tid=target_tid,
                              data_url=data_url, remarks=remarks)
            prop.observations.append(obs)
            return oid

    def get_observations(self, pid: int) -> List[Observation]:
        """Return all observations for a proposal."""
        with self._lock:
            return list(self._proposals[pid].observations)