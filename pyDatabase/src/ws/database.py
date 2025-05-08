import sqlite3
from typing import List, NamedTuple

# Constants
STATUS_INITIAL_PROPOSAL = 0
STATUS_NO_SUCH_PROPOSAL = -999

# Define simple data structures
class Position(NamedTuple):
    ra: float
    dec: float

class Target(NamedTuple):
    position: Position
    exposure_time: float
    identifier: str

def initialize_db(db_name: str = 'astronomy.db'):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

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

    conn.commit()
    conn.close()

def store_proposal(targets: List[Target], db_name: str = 'astronomy.db') -> int:
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

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

    conn.commit()
    conn.close()

    return proposal_id





def long getProposalStatus(long proposal_id):
    dbConnection = sqlite3.connect(db_name)
    cursor = dbConnection.cursor()
    cursor.execute('SELECT * FROM Database WHERE ID = ? AND status = ? ', (proposal_id,proposalStatus)) 
    
    result = cursor.fetchall()
    proposal_id, proposalStatus = result
    
    dbConnection.close()

    if proposal_id:
        return proposalStatus

    return STATUS_NO_SUCH_PROPOSAL 




def removeProposal(long proposal_id):
    result = getProposalStatus(proposal_id)
    if result:
        dbConnection = sqlite3.connect(db_name)
        cursor = dbConnection.cursor()
        cursor.execute('DELETE FROM proposals WHERE id = ?', (proposal_id,))

        dbConnection.commit()
        dbConnection.close()

    else:
        return
        

