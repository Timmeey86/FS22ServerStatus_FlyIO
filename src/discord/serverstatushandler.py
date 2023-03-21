from threading import Lock
from fs22.fs22server import OnlineState
import asyncio
import discord
import traceback
import copy

class ServerStatusConfig:
    """This class stores the fixed information about a server status reporting channel"""

    def __init__(self, title, icon, color, channelId):
        self.title = title
        self.icon = icon
        self.color = color
        self.channelId = channelId

class ServerStatusMessage:
    """Stores a message to be published in the server status message channel"""
    
    def __init__(self, isOnlineMessage = False, isOfflineMessage = False):
        self.isOnlineMessage = isOnlineMessage
        self.isOfflineMessage = isOfflineMessage

class ServerStatusHandler:
    """This class is responsible for posting messages whenever the server goes offline or comes back online"""

    def debugPrint(self, message):
        if self.debug == True:
            print("[DEBUG] [ServerStatusHandler] %s" % message)

    def __init__(self, discordClient):
        self.configs = {} # Stores a configuration object for every tracked server
        self.pendingData = {} # Stores a list of messages for every tracked server to be posted
        self.lock = Lock()
        self.enabled = True
        self.task = None
        self.discordClient = discordClient
        self.debug = False

    def add_config(self, serverId, serverStatusConfig):
        with self.lock:
            self.configs[serverId] = serverStatusConfig
            self.pendingData[serverId] = []

    async def track_server(self, serverId, interaction, title, icon, color):
        # TOOD: Status message about the server being tracked
        serverStatusConfig = ServerStatusConfig(title, icon, color, interaction.channel_id)
        self.add_config(serverId, serverStatusConfig)
        
    ### Threading ###

    def start(self):
        if self.task is None:
            self.enabled = True
            self.task = asyncio.create_task(self.post_pending_messages())

    def stop(self):
        if self.task is not None:
            self.enabled = False

    ### Discord update ###

    async def post_pending_messages(self):
        while self.enabled == True:
            # Give discord a chance to relax
            await asyncio.sleep(60)
            self.debugPrint("Waking up")
            # Copy configs and pending data (keep the lock short)
            with self.lock:
                configsCopy = copy.deepcopy(self.configs)
                pendingDataCopy = {}
                for serverId in self.pendingData:
                    pendingDataCopy[serverId] = copy.deepcopy(self.pendingData[serverId])
                    self.pendingData[serverId] = []
            self.debugPrint("Copied data")
            # Process copied data now
            for serverId in configsCopy:
                if len(pendingDataCopy[serverId]) > 0:
                    self.debugPrint("Processing messages for server ID %s" % serverId)
                    data = pendingDataCopy[serverId]
                    config = configsCopy[serverId]

                    self.debugPrint("Trying to find channel")

                    try:
                        channel = self.discordClient.get_channel(config.channelId)
                    except:
                        # This could e.g. happen in case of Cloudflare rate limiting
                        print("[WARN ] [ServerStatusHandler] Failed to retrieve server log channel ID: %s" % traceback.format_exc())
                        continue
                    
                    # Create a new embed for each message
                    for entry in data:
                        if entry.isOnlineMessage:
                            indicator = "🟢"
                            statusPart = "now online"
                        elif entry.isOfflineMessage:
                            indicator = "🔴"
                            statusPart = "now offline"
                            
                        try:
                            message = "%s %s **%s** is %s" % (indicator, config.icon, config.title, statusPart)
                            embed = discord.Embed(description=message, color=int(overrideColor,16))
                            await channel.send(embed=embed)
                        except:
                            print("[WARN ] [ServerStatusHandler] Failed creating a player status embed: %s" % traceback.format_exc())

                        # don't spam messages
                        await asyncio.sleep(1)

        print("[INFO ] [ServerStatusHandler] ServerStatusHandler was aborted")
        self.task = None

    ### Event listeners ###

    def on_server_status_changed(self, serverId, serverData):
        with self.lock:
            if serverId in self.pendingData:
                self.pendingData[serverId].append(ServerStatusMessage(
                        isOnlineMessage=serverData.status == OnlineState.Online,
                        isOfflineMessage=serverData.status == OnlineState.Offline))