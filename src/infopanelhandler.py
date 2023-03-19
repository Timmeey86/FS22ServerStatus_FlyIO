from queue import Queue
from threading import Lock
import asyncio

class InfoPanelConfig:
    """This class stores the fixed information about an info panel which doesn't change for a server usually."""

    def __init__(self, ip, port, flag, title, guildId, channelId, embedId, serverColor):
        self.ip = ip
        self.port = port
        self.flag = flag
        self.title = title
        self.serverColor = serverColor
        self.guildId = guildId
        self.channelId = channelId
        self.embedId = embedId


class InfoPanelHandler:
    """This class is responsible for updating the info panel in the configured discord channel"""

    def __init__(self):
        self.configs = {}           # Stores the info panel configurations for each server ID
        # Stores the current data which needs to be published for each server ID
        self.pendingServerData = {}
        self.currentServerData = {}  # Stores the most recently received data
        self.lock = Lock()
        self.enabled = True
        self.task = None

    def add_config(self, serverId, discordInfoPanelConfig):
        with self.lock:
            self.configs[serverId] = discordInfoPanelConfig
            self.pendingServerData[serverId] = None

    ### Threading ###

    def start(self):
        if self.task is None:
            self.enabled = True
            self.task = asyncio.create_task(self.update_panels())

    def stop(self):
        if self.task is not None:
            self.enabled = False

    ### Discord update ###

    async def update_panels(self):
        while self.enabled == True:
            await asyncio.sleep(10)
            print("[InfoPanelHandler] Checking for panel update")
            with self.lock:
                for serverId in self.configs:
                    if serverId in self.pendingServerData and self.pendingServerData[serverId] is not None:
                        data = self.pendingServerData[serverId]
                        config = self.configs[serverId]
                        print("[InfoPanelHandler] Updating server %s (%s) with server name %s" %
                              (serverId, config.title, data.serverName))
                        # Don't process again until there is a new update
                        self.pendingServerData[serverId] = None
        print("[InfoPanelHandler] InfoPanelHandler was aborted")
        self.task = None

    ### Event listeners ###

    def on_initial_event(self, serverId, serverData):
        with self.lock:
            self.pendingServerData[serverId] = serverData

    def on_updated(self, serverId, serverData):
        """Queues the current server data for being sent to discord on each update.
        The discord embed will be updated at fixed time intervals."""
        with self.lock:
            self.pendingServerData[serverId] = serverData

    def getText(self, serverConfig, serverData):
        message = \
            "**Map: **" + serverData.map + "\r\n" + \
            "**Status: **" + serverData.status + "\r\n" + \
            "**Server Time: **" + self.get_server_time(serverData) + "\r\n" + \
            "**Mods Link: **" + self.get_mods_link(serverConfig) + "\r\n" + \
            "**Players Online: **" + str(serverData.online_player_count()) + "/" + serverData.maxPlayers + "\r\n" + \
            "**Players: **"

        if not serverData.players:
            replyMessage = replyMessage + "(none)"
        else:
            for playerName in serverData.players:
                replyMessage = replyMessage + "\r\n - %s (%s min)" % (
                    playerName, serverData.players[playerName].onlineTime)

    def get_server_time(self, serverData):
        totalsec, _ = divmod(int(serverData.dayTime), 1000)
        totalmin, _ = divmod(totalsec, 60)
        hours, minutes = divmod(totalmin, 60)
        return f'{hours:02d}:{minutes:02d}'

    def get_mods_link(self, serverConfig):
        """Retrieves the link to the mods page"""
        return "http://%s:%s/mods.html" % (serverConfig.ip, serverConfig.port)
