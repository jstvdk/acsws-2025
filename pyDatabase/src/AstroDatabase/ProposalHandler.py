import threading
import itertools

import DATABASE_MODULE__POA

import TYPES
from Acspy.Servants.ACSComponent import ACSComponent
from Acspy.Servants.ContainerServices import ContainerServices
from Acspy.Servants.ComponentLifecycle import ComponentLifecycle


STATUS_INITIAL_PROPOSAL     = 0
STATUS_RUNNING_PROPOSAL     = 1
STATUS_READY_PROPOSAL       = 2
STATUS_NO_SUCH_PROPOSAL     = -999

class ProposalHandler(
    DATABASE_MODULE__POA.DataBase,
    ACSComponent,
    ContainerServices,
    ComponentLifecycle
):
    def __init__(self):
        ACSComponent.__init__(self)
        ContainerServices.__init__(self)
        self._logger = self.getLogger()

        # thread‐safe in-memory storage
        self._lock      = threading.Lock()
        self._pid_gen   = itertools.count(1)
        self._oid_gen   = itertools.count(1)
        # pid → { targets: [Target], status: int }
        self._proposals = {}
        # (pid, tid) → image
        self._images    = {}

    def storeProposal(self, targets: TYPES.TargetList) -> int:
        with self._lock:
            pid = next(self._pid_gen)
            # ensure tid uniqueness within this list
            tids = [t.tid for t in targets]
            if len(tids) != len(set(tids)):
                raise ValueError("All target.tid must be unique within a proposal")
            self._proposals[pid] = {
                "targets": list(targets),
                "status":  STATUS_INITIAL_PROPOSAL
            }
            self._logger.info(f"[storeProposal] pid={pid}, {len(targets)} targets")
            return pid

    def getProposalStatus(self, pid: int) -> int:
        with self._lock:
            entry = self._proposals.get(pid)
            return entry["status"] if entry else STATUS_NO_SUCH_PROPOSAL

    def removeProposal(self, pid: int) -> None:
        with self._lock:
            if pid in self._proposals:
                del self._proposals[pid]
                # also remove any stored images
                self._images = {k:v for k,v in self._images.items() if k[0]!=pid}
                self._logger.info(f"[removeProposal] pid={pid}")

    def getProposalObservations(self, pid: int) -> TYPES.ImageList:
        with self._lock:
            entry = self._proposals.get(pid)
            if entry is None:
                # unknown pid → treat as not ready
                raise SYSTEMErr.ProposalNotYetReadyEx()
            status = entry["status"]
            if status != STATUS_READY_PROPOSAL:
                raise SYSTEMErr.ProposalNotYetReadyEx()
            # collect images for this pid
            images = [
                image
                for (p, _tid), image in self._images.items()
                if p == pid
            ]
            return TYPES.ImageList(images)

    def getProposals(self) -> TYPES.ProposalList:
        with self._lock:
            queued = []
            for pid, entry in self._proposals.items():
                if entry["status"] == STATUS_INITIAL_PROPOSAL:
                    queued.append(
                        TYPES.Proposal(
                            pid=pid,
                            targets=TYPES.TargetList(entry["targets"]),
                            status=entry["status"]
                        )
                    )
            return TYPES.ProposalList(queued)

    def setProposalStatus(self, pid: int, status: int) -> None:
        with self._lock:
            entry = self._proposals.get(pid)
            if entry is None:
                # no such proposal → no-op or could raise, but spec doesn’t say
                return
            old = entry["status"]
            # only allow 0→1 or 1→2
            if not ((old == STATUS_INITIAL_PROPOSAL and status == STATUS_RUNNING_PROPOSAL) or
                    (old == STATUS_RUNNING_PROPOSAL and status == STATUS_READY_PROPOSAL)):
                raise SYSTEMErr.InvalidProposalStatusTransitionEx()
            entry["status"] = status
            self._logger.info(f"[setProposalStatus] pid={pid} {old}→{status}")

    def storeImage(
        self,
        pid: int,
        tid: int,
        image: TYPES.ImageType
    ) -> None:
        with self._lock:
            entry = self._proposals.get(pid)
            if entry is None:
                raise KeyError(f"No such proposal: {pid}")
            # check that tid exists on that proposal
            if not any(t.tid == tid for t in entry["targets"]):
                raise KeyError(f"Target {tid} not found in proposal {pid}")
            key = (pid, tid)
            if key in self._images:
                raise SYSTEMErr.ImageAlreadyStoredEx()
            # store it
            self._images[key] = image
            self._logger.info(f"[storeImage] pid={pid}, tid={tid}")

    def clean(self) -> None:
        with self._lock:
            self._proposals.clear()
            self._images.clear()
            self._pid_gen = itertools.count(1)
            self._oid_gen = itertools.count(1)
            self._logger.info("[clean] all in-memory data wiped")