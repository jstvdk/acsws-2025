import sqlite3
from pathlib import Path
import threading
import TYPES
import SYSTEMErrImpl
import datetime

import DATABASE_MODULE__POA      # IDL stubs
from Acspy.Servants.ACSComponent import ACSComponent
from Acspy.Servants.ContainerServices import ContainerServices
from Acspy.Servants.ComponentLifecycle import ComponentLifecycle


DB_DIR   = Path(__file__).resolve().parent / "data"
DB_DIR.mkdir(exist_ok=True)

STATUS_INITIAL_PROPOSAL = 0
STATUS_NO_SUCH_PROPOSAL = -999

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

/* ------------------------------------------------------------------
   proposal
   ------------------------------------------------------------------*/
CREATE TABLE IF NOT EXISTS proposal (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    status      INTEGER NOT NULL,                         -- 0/1/2
    created_at  DATETIME NOT NULL DEFAULT (datetime('now')),
    updated_at  DATETIME NOT NULL DEFAULT (datetime('now'))
);

/* ------------------------------------------------------------------
   target  (belongs to one proposal)
   ------------------------------------------------------------------*/
CREATE TABLE IF NOT EXISTS target (
    id              INTEGER  PRIMARY KEY AUTOINCREMENT,   -- internal
    proposal_id     INTEGER  NOT NULL
                           REFERENCES proposal(id) ON DELETE CASCADE,
    targ_id         TEXT     NOT NULL,    -- astronomer-supplied identifier
    ra              REAL     NOT NULL,    -- or lon / az, adjust if needed
    dec             REAL     NOT NULL,    -- or lat / el
    exposure_time   REAL     NOT NULL,    -- seconds
    UNIQUE (proposal_id, targ_id)         -- “unique per proposal”
);

/* ------------------------------------------------------------------
   image  (one per target in a proposal, after obs is ready)
   ------------------------------------------------------------------*/
CREATE TABLE IF NOT EXISTS image (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    proposal_id INTEGER NOT NULL
                           REFERENCES proposal(id) ON DELETE CASCADE,
    target_id   INTEGER NOT NULL
                           REFERENCES target(id)   ON DELETE CASCADE,
    file_uri    TEXT    NOT NULL,
    captured_at DATETIME NOT NULL DEFAULT (datetime('now')),
    meta_json   TEXT,
    UNIQUE (proposal_id, target_id)       -- raises duplicate error itself
);
"""

class ProposalHandler(DATABASE_MODULE__POA.DataBase,
                      ACSComponent,
                      ContainerServices,
                      ComponentLifecycle):

    def __init__(self):
        ACSComponent.__init__(self)
        ContainerServices.__init__(self)

        self._logger = self.getLogger()

        self.db_file  = DB_DIR / "proposals.sqlite"
        
        self._db = sqlite3.connect(self.db_file, detect_types=sqlite3.PARSE_DECLTYPES)


    def execute(self):
        with self._lock:
            self._db   = sqlite3.connect(self.db_file,
                                        check_same_thread=False)  # <── key change
            self._lock = threading.Lock()
            self._db.execute("PRAGMA journal_mode = WAL;")      # better concurrency
            self._db.execute("PRAGMA synchronous  = NORMAL;")   # good durability/latency trade-off
            self._db.execute("PRAGMA foreign_keys=ON;")
            
            self._db.executescript(SCHEMA_SQL)
            self._logger.info(f"SQLite initialised at {self.db_file}")

    def storeProposal(self, targets):
        """
        Create a proposal in status 0 (queued) and its N targets.
        Returns the new proposal ID.
        """
        with self._lock:
            cur = self._db.cursor()
            cur.execute("BEGIN;")
            cur.execute("INSERT INTO proposal(status) VALUES (?)",
                        (STATUS_INITIAL_PROPOSAL,))
            pid = cur.lastrowid

            cur.executemany(
                "INSERT INTO target(proposal_id, ra, dec, name) "
                "VALUES (?,?,?,?)",
                [(pid,
                  t.ra,
                  t.dec,
                  getattr(t, "name", None))            # name may be absent
                 for t in targets]
            )
            self._db.commit()
        return pid

    def getProposalStatus(self, pid: int) -> int:
        with self._lock:
            cur = self._db.execute(
                "SELECT status FROM proposal WHERE id=?", (pid,))
            row = cur.fetchone()
            return row[0] if row else STATUS_NO_SUCH_PROPOSAL

    def removeProposal(self, pid: int) -> None:
        with self._lock:
            self._db.execute("DELETE FROM proposal WHERE id=?", (pid,))
            self._db.commit()

    def getProposalObservations(self, pid: int) -> TYPES.ImageList:
        """Returns a list of dummy images for a proposal."""
        return TYPES.ImageList()

    def getProposals(self) -> list:
        """Returns a list of dummy pending proposals."""
        return TYPES.ProposalList()

    def setProposalStatus(self, pid: int, status: int) -> None:
        """Sets a proposal status. Dummy implementation does nothing."""
        pass

    def storeImage(self, pid: int, tid: int, image: TYPES.ImageType) -> None:
        """Stores an image for a proposal and target. Dummy implementation does nothing."""
        return None

    def cleanUp(self): 
        with self._lock:
            try:
                self._db.close()
            finally:
                super().cleanUp()
