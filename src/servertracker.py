from events import Events
from fs22server import FS22ServerAccess, FS22ServerStatus, FS22ServerConfig, OnlineState
from queue import Queue
import asyncio


class ServerTrackerEvents(Events):
    """Defines events to be subscribed to"""
    __events__ = ('playerWentOffline', 'playerWentOnline', 'serverWentOffline',
                  'serverWentOnline', 'playerAdminStateChanged', 'playerCountChanged', 'onlineStateChanged', 'updated')


class ServerTracker:
    """Tracks a single FS22 server and sends events whenever something changes"""

    def __init__(self, serverConfig):
        self.events = ServerTrackerEvents()
        self.lastKnownServerState = FS22ServerStatus()
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
        while not self.cancelled:
            try:
                currentStatus = self.serverAccess.get_current_status()
                if currentStatus is not None:
                    print("Server %s is %s with %s players" % (currentStatus.serverName,
                        currentStatus.status.name, len(currentStatus.onlinePlayers)))
                else:
                    print("No status")
            except Exception as e:
                print("Error: %s" % e)
            await asyncio.sleep(5)
