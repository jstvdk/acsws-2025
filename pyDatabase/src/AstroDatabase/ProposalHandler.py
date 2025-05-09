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
    pid    INTEGER  NOT NULL
                           REFERENCES proposal(id) ON DELETE CASCADE,
    tid         TEXT     NOT NULL,   
    az              REAL     NOT NULL,    
    el             REAL     NOT NULL,    
    exposure_time   REAL     NOT NULL,    -- seconds
    UNIQUE (proposal_id, targ_id)         
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
        
        self._db   = sqlite3.connect(self.db_file,
                                    check_same_thread=False)
        self._db.executescript(SCHEMA_SQL)
        self._logger.info(f"SQLite initialised at {self.db_file}")
        


    def execute(self):
        self.cur = self._db.cursor()
        
        self._logger.info(f"Cursor was initialized inside the execute() method")

    def storeProposal(self, targets):
        """
        Create a proposal in status 0 (queued) and its N targets.
        Returns the new proposal ID.
        """
            
        self.cur.execute("BEGIN;")
        self.cur.execute("INSERT INTO proposal(status) VALUES (?)",
                    (STATUS_INITIAL_PROPOSAL,))
        pid = self.cur.lastrowid

        self.cur.executemany(
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

        self.cur = self._db.execute(
            "SELECT status FROM proposal WHERE id=?", (pid,))
        row = self.cur.fetchone()
        return row[0] if row else STATUS_NO_SUCH_PROPOSAL

    def removeProposal(self, pid: int) -> None:
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

        try:
            self._db.close()
        finally:
            super().cleanUp()
