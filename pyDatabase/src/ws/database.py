import Database__POA
import Database

import sqlite3
from typing import List, NamedTuple
from Acspy.Servants.ACSComponent import ACSComponent
from Acspy.Servants.ContainerServices import ContainerServices
from Acspy.Servants.ComponentLifecycle import ComponentLifecycle



# Status constants
STATUS_INITIAL_PROPOSAL = 0  # queued
STATUS_RUNNING = 1            # running
STATUS_READY = 2              # ready
# As defined in IDL: const long STATUS_NO_SUCH_PROPOSAL = -999
STATUS_NO_SUCH_PROPOSAL = -999


#Data types
class Target:
    def __init__(self, position: str, exposure_time: float, target_id: str):
        self.position = position
        self.exposure_time = exposure_time
        self.target_id = target_id

class TargetList(list):
    “”"A list of Target objects.“”"
    pass

class ImageType:
    def __init__(self, data: bytes):
        self.data = data

class ImageList(list):
    “”"A list of ImageType objects.“”"
    pass

class ProposalList(list):
    “”"A list of proposal IDs.“”"
    pass

class AstroDatabase(Database__POA, ACSComponent, ContainerServices, ComponentLifecycle):
    def __init__(self):
        ACSComponent.__init__(self)
        ContainerServices.__init__(self)
        self._logger = self.getLogger()





    def initialize_db(db_name: str = 'astronomy.db'):
        dbConnection = sqlite3.connect(db_name)
        cursor = dbConnection.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS proposals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status INTEGER NOT NULL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS targets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proposal_id INTEGER NOT NULL,
                target_identifier TEXT NOT NULL,
                exposure_time REAL NOT NULL,
                ra REAL NOT NULL,
                dec REAL NOT NULL,
                UNIQUE(proposal_id, target_identifier),
                FOREIGN KEY(proposal_id) REFERENCES proposals(id)
            )
        ''')

        dbConnection.commit()
        dbConnection.close()

    def store_proposal(targets: List[Target], db_name: str = 'astronomy.db') -> int:
        """Stores a new proposal. Returns a proposal ID """
        dbConnection = sqlite3.connect(db_name)
        cursor = dbConnection.cursor()


        # Insert a new proposal and retrieve its ID
        cursor.execute('INSERT INTO proposals (status) VALUES (?)', (STATUS_INITIAL_PROPOSAL,))
        proposal_id = cursor.lastrowid

        # Insert associated targets
        for target in targets:
            cursor.execute('''
                INSERT INTO targets (proposal_id, target_identifier, exposure_time, ra, dec)
                VALUES (?, ?, ?, ?, ?)
            ''', (proposal_id, target.identifier, target.exposure_time,
                  target.position.ra, target.position.dec))

        dbConnection.commit()
        dbConnection.close()

        return proposal_id



     def getProposalStatus(self, pid: int) -> int:
         """Gets the status of a proposal."""  
        dbConnection = sqlite3.connect(db_name)
        cursor = dbConnection.cursor()
        cursor.execute('SELECT * FROM Database WHERE ID = ? AND status = ? ', (proposal_id,proposalStatus)) 
        
        result = cursor.fetchall()
        proposal_id, proposalStatus = result
        
        dbConnection.close()

        if proposal_id:
            return proposalStatus

        return STATUS_NO_SUCH_PROPOSAL

            
    def removeProposal(self, pid: int) -> None:
        """Removes a proposal"""
        result = getProposalStatus(proposal_id)
        if result:
            dbConnection = sqlite3.connect(db_name)
            cursor = dbConnection.cursor()
            cursor.execute('DELETE FROM proposals WHERE id = ?', (proposal_id,))

            dbConnection.commit()
            dbConnection.close()

        else:
            return None




    def getProposalObservations(self, pid: int) -> list:
            """Returns a list of dummy images for a proposal."""
            return []

    def getProposals(self) -> list:
            """Returns a list of dummy pending proposals."""
            return []

    def setProposalStatus(self, pid: int, status: int) -> None:
            """Sets a proposal status. Dummy implementation does nothing."""
            return None

    def storeImage(self, pid: int, tid: int, image: Any) -> None:
            """Stores an image for a proposal and target. Dummy implementation does nothing."""
            return None
