from Acspy.Clients.SimpleClient import PySimpleClient
import TYPES

cli = PySimpleClient()
comp = cli.getComponent("ACS_astroDatabase")

print(f'The Component was retrieved succesfuly and proposal status is : {comp.getProposalStatus(1)}')
