from Acspy.Clients.SimpleClient import PySimpleClient

cli = PySimpleClient()
comp = cli.getComponent("ACS_astroDatabase")

print(comp.storeProposal([4]))
