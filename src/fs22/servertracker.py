from events import Events
from fs22.fs22server import FS22ServerAccess, FS22ServerStatus, FS22ServerConfig, OnlineState
from queue import Queue
import asyncio
import traceback


class ServerTrackerEvents(Events):
    """Defines events to be subscribed to"""
    __events__ = ('playerWentOffline', 'playerWentOnline', 'serverStatusChanged',
                  'playerAdminStateChanged', 'playerCountChanged', 'updated', 'initial')


class ServerTracker:
    """Tracks a single FS22 server and sends events whenever something changes"""

    def __init__(self, serverConfig):
        self.events = ServerTrackerEvents()
        self.lastknownServerData = FS22ServerStatus()
        self.serverId = serverConfig.id
        self.serverAccess = FS22ServerAccess(serverConfig)
        self.task = None
        self.cancelled = False

    def start_tracker(self):
        self.cancelled = False
        self.task = asyncio.create_task(self.track_server_status())

    def stop_tracker(self):
        self.cancelled = True

    async def track_server_status(self):
        firstTime = True
        print("[ServerTracker] Server tracking has started")
        while not self.cancelled:
            try:
                currentData = self.serverAccess.get_current_status()

                # Send a single initial update when tracking starts
                if firstTime:
                    self.events.initial(self.serverId, currentData)
                    firstTime = False

                # Send other events for every update
                if currentData is not None:
                    self.send_events(currentData)
                    self.lastknownServerData = currentData
                else:
                    print("[ServerTracker] No status")
            except Exception:
                print(f"[ServerTracker] Error: {traceback.format_exc()}")
            await asyncio.sleep(5)

        print("[ServerTracker] Server tracking has stopped")

    def send_events(self, currentData):

        # Handle players which are now offline first, in case the server went down or they logged on another server
        for playerName in self.lastknownServerData.onlinePlayers:
            if playerName not in currentData.onlinePlayers:
                self.events.playerWentOffline(self.serverId, playerName)

        # Handle server state changes and send full data in that case
        if self.lastknownServerData.status != currentData.status:
            print(f"[INFO ] [ServerTracker] Server {self.serverId} is now {currentData.status}")
            self.events.serverStatusChanged(self.serverId, currentData)

        # Handle recently logged in players now
        for playerName in currentData.onlinePlayers:
            if playerName not in self.lastknownServerData.onlinePlayers:
                self.events.playerWentOnline(self.serverId, playerName)

            if ((playerName not in self.lastknownServerData.onlinePlayers or
                    self.lastknownServerData.onlinePlayers[playerName].isAdmin == "false")
                    and currentData.onlinePlayers[playerName].isAdmin == "true"):
                self.events.playerAdminStateChanged(self.serverId, playerName)

        # Send a single event whenever the player count changed, for listeners which do not need to know which players are online
        if len(self.lastknownServerData.onlinePlayers) != len(currentData.onlinePlayers):
            self.events.playerCountChanged(
                self.serverId, len(currentData.onlinePlayers))

        # Send an update event with full data to handle any remaining case in the listener
        self.events.updated(self.serverId, currentData)
