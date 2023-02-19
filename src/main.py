import asyncio
from fs22server import FS22ServerConfig
from servertracker import ServerTracker
from dotenv import load_dotenv
import os

def initial(serverId, serverData):
    print("Received initial event for server %s" % (serverId))
    
def updated(serverId, serverData):
    #print("Received update event for server %s" % (serverId, serverData.__dict__))
    pass

def playerWentOnline(serverId, playerName):
    print("Player %s joined server %s" % (playerName, serverId))

def playerWentOffline(serverId, playerName):    
    print("Player %s logged out from server %s" % (playerName, serverId))

def serverStatusChanged(serverId, serverData):
    print("Server %s is now %s" % (serverId, serverData.status.name))

def playerAdminStateChanged(serverId, playerName):
    print("Player %s is now an admin" % (playerName))

async def main():

    if os.getenv("SERVER_A_IP") is None:
        print("Loading local environment")
        load_dotenv()
    else:
        print("Using existing environment")
    

    serverA = FS22ServerConfig(0, os.getenv("SERVER_A_IP"), os.getenv(
        "SERVER_A_PORT"), os.getenv("SERVER_A_APICODE"))
    serverB = FS22ServerConfig(1, os.getenv("SERVER_B_IP"), os.getenv(
        "SERVER_B_PORT"), os.getenv("SERVER_B_APICODE"))
    serverC = FS22ServerConfig(2, os.getenv("SERVER_C_IP"), os.getenv(
        "SERVER_C_PORT"), os.getenv("SERVER_C_APICODE"))
    serverD = FS22ServerConfig(3, os.getenv("SERVER_D_IP"), os.getenv(
        "SERVER_D_PORT"), os.getenv("SERVER_D_APICODE"))

    serverConfigs = [serverA, serverB, serverC, serverD]

    for serverConfig in serverConfigs:
        tracker = ServerTracker(serverConfig)
        tracker.events.initial += initial
        tracker.events.updated += updated
        tracker.events.playerWentOnline += playerWentOnline
        tracker.events.playerWentOffline += playerWentOffline
        tracker.events.serverStatusChanged += serverStatusChanged
        tracker.events.playerAdminStateChanged += playerAdminStateChanged
        tracker.start_tracker()

    print("Finished initialization")

    while(True):
        await asyncio.sleep(5)

print("Done")

asyncio.run(main())
