import sqlite3


def long storeProposal(TYPES::TargetList targets):
    Database

    return ID_proposal


def long getProposalStatus(long ID_proposal):
    dbConnection = sqlite3.connect(databasePath)
    cursor = dbConection.cursor()
    cursor.execute('SELECT * FROM Database WHERE ID = ? AND status = ? ', (ID_proposal,proposalStatus)) 
    
    result = cursor.fetchall()
    ID_proposal, proposalStatus = result
    
    if ID_proposal:
        return proposalStatus
    else:
        print(STATUS_NO_SUCH_PROPOSAL)

    












def removeProposal():
    return

def ProposalList()
