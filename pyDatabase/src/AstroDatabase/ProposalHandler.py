import sqlite3
from pathlib import Path
import TYPES
import SYSTEMErrImpl
import os 
import DATABASE_MODULE__POA
from Acspy.Servants.ACSComponent import ACSComponent
from Acspy.Servants.ContainerServices import ContainerServices
from Acspy.Servants.ComponentLifecycle import ComponentLifecycle


DB_DIR   = Path(__file__).resolve().parent / "data"
DB_DIR.mkdir(exist_ok=True)

STATUS_INITIAL_PROPOSAL = -1
STATUS_QUEUED_PROPOSAL = 0
STATUS_RUNNING = 1
STATUS_READY = 2
STATUS_NO_SUCH_PROPOSAL = -999


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

/* ---------- proposal ---------- */
CREATE TABLE IF NOT EXISTS proposal (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    status INTEGER NOT NULL              -- 0 = queued, 1 = running, 2 = ready
);

/* ---------- target (many per proposal) ---------- */
CREATE TABLE IF NOT EXISTS target (
    id            INTEGER  PRIMARY KEY AUTOINCREMENT,
    proposal_id   INTEGER  NOT NULL
                           REFERENCES proposal(id) ON DELETE CASCADE,
    tid       TEXT     NOT NULL,      -- astronomers identifier
    az            REAL     NOT NULL,
    el            REAL     NOT NULL,
    exposure_time INTEGER     NOT NULL,      -- seconds
    UNIQUE (proposal_id, tid)         -- “unique per proposal”
);

/* ---------- image (one per target, after obs) ---------- */
CREATE TABLE IF NOT EXISTS image (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    proposal_id  INTEGER NOT NULL
                  REFERENCES proposal(id) ON DELETE CASCADE,
    target_id    INTEGER NOT NULL
                  REFERENCES target(id)   ON DELETE CASCADE,
    image_array   BLOB    NOT NULL,              -- raw image bytes
    UNIQUE (proposal_id, target_id)
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

    def storeProposal(self, targets: TYPES.TargetList) -> int:
        """
        Create a proposal in status 0 and its N targets;
        always commit on success, rollback on any exception.
        """
        cur = self._db.cursor()
        self._logger.info(f"Storing proposal with {len(targets)} targets")
        try:

            cur.execute(
                "INSERT INTO proposal(status) VALUES (?)",
                (STATUS_INITIAL_PROPOSAL,)
            )
            pid = cur.lastrowid

            cur.executemany(
                """
                INSERT INTO target (proposal_id, tid, az, el, exposure_time)
                VALUES (?,?,?,?,?)
                """,
                [
                    (
                        pid,
                        t.tid,
                        t.coordinates.az,
                        t.coordinates.el,
                        t.expTime
                    )
                    for t in targets
                ]
            )

            self._db.commit()
            return pid

        except Exception as e:
            self._db.rollback()
            self._logger.error("Error with inserting proposal and targets")
            raise SYSTEMErrImpl.InvalidProposalStatusTransitionExImpl()


    def getProposalStatus(self, pid: int) -> int:
        self.cur = self._db.execute(
            "SELECT status FROM proposal WHERE id=?", (pid,))
        row = self.cur.fetchone()
        return row[0] if row else STATUS_NO_SUCH_PROPOSAL

    def removeProposal(self, pid: int) -> None:
        self._logger.info(f"Removing proposal {pid}")
        self._db.execute("DELETE FROM proposal WHERE id=?", (pid,))
        self._db.commit()

    def storeImage(self, pid: int, tid: int, image: TYPES.ImageType) -> None:
        """
        Stores raw-image bytes for (proposal_id, target_id).
        Raises ImageAlreadyStoredEx on duplicate or FK error.
        """
        self._logger.info(f"Storing image for proposal {pid} and target {tid} that looks like  {image} ")
        try:
            self.cur.execute(
                """
                INSERT INTO image (proposal_id, target_id, image_array)
                VALUES (?,?,?)
                """,
                (pid, tid, sqlite3.Binary(image))
            )
            self._db.commit()

        except Exception as e:
            self._db.rollback()
            raise SYSTEMErrImpl.ImageAlreadyStoredExImpl(str(e))

    def getProposalObservations(self, pid: int) -> TYPES.ImageList:
        """
        Returns a TYPES.ImageList of raw-image bytes for a READY proposal.
        Raises ProposalNotYetReadyEx if status != STATUS_READY.
        """
        if self.getProposalStatus(pid) != STATUS_READY:
            raise SYSTEMErrImpl.ProposalNotYetReadyExImpl()

        self.cur.execute(
            "SELECT image_array FROM image WHERE proposal_id = ? ORDER BY id",
            (pid,)
        )
        rows = self.cur.fetchall()  # list of (bytes,) tuples

        img_list = TYPES.ImageList()
        img_list.length(len(rows))
        for i, (blob,) in enumerate(rows):
            img_list[i] = blob

        return img_list

    def setProposalStatus(self, pid: int, status: int) -> None:
        """
        Set the proposal status, allowing only:
        -1 (initial) → 0 (queued)
        0 (queued)  → 1 (running)
        1 (running) → 2 (ready)

        Raises InvalidProposalStatusTransitionEx otherwise.
        """

        self.cur.execute(
            "SELECT status FROM proposal WHERE id = ?",
            (pid,)
        )
        row = self.cur.fetchone()
        if row is None:
            raise SYSTEMErrImpl.InvalidProposalStatusTransitionExImpl(
                f"No proposal with id={pid}"
            )

        current = row[0]

        if not ((current == -1 and status == 0) or
                (current == 0  and status == 1) or
                (current == 1  and status == 2)):
            raise SYSTEMErrImpl.InvalidProposalStatusTransitionExImpl()

        self._logger.info(
            f"The status of the proposal {pid} is changed from {current} to {status}"
        )
        self.cur.execute(
            "UPDATE proposal SET status = ? WHERE id = ?",
            (status, pid)
        )
        self._db.commit()

    def getProposals(self) -> list:
        """
        Return a list of Proposal structs for all proposals in the queued state (status = 0).
        If none are queued, returns an empty list.
        """
        self._logger.info("Getting all proposals in the queued state")
        
        self.cur.execute(
            "SELECT id, status FROM proposal WHERE status = ? ORDER BY id",
            (STATUS_QUEUED_PROPOSAL,)
        )
        proposals: list = []
        
        for pid, status in self.cur.fetchall():
            self._logger.info(f"Found queued proposal {pid}")
            
            self.cur.execute(
                """
                SELECT id, az, el, exposure_time
                FROM target
                WHERE proposal_id = ?
                ORDER BY id
                """,
                (pid,)
            )
            targets = []
            for tid, az, el, exp_time in self.cur.fetchall():
                pos = TYPES.Position(az, el)
                tgt = TYPES.Target(tid, pos, exp_time)
                targets.append(tgt)

            prop = TYPES.Proposal(pid, targets, status)
            self._logger.info(f"Proposal looks like {prop}")
            proposals.append(prop)
        self._logger.info(f"Proposal list looks like {proposals}")
        return proposals

    def clean(self) -> None:
        """
        Clean all the proposals (and their targets/images via ON DELETE CASCADE).
        """
        self._logger.info("Cleaning all proposals from the database")
        self.cur.execute("DELETE FROM proposal")
        self._db.commit()
    
    def cleanUp(self):
        self._logger.info("Cleaning up the database")
        try:
            self.clean()
            self._db.close()
        except:
            pass
        super().cleanUp()
