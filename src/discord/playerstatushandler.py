from threading import Lock
import asyncio
import discord
import traceback
import copy
import time

class PlayerStatusConfig:
    """This class stores the fixed information about a player status reporting channel"""

    def __init__(self, title, icon, color, channel):
        self.title = title
        self.icon = icon
        self.color = color
        self.channel = channel

class PlayerStatusMessage:
    """Stores a message to be published in the player status message channel"""

    def __init__(self, player, isOnlineMessage = False, isOfflineMessage = False, isAdminMessage = False):
        self.isOnlineMessage = isOnlineMessage
        self.isOfflineMessage = isOfflineMessage
        self.isAdminMessage = isAdminMessage
        self.player = player

class PlayerStatusHandler:
    """This class is responsible for posting messages in the following situations:
    - A player joins a server
    - A player leaves a server
    - A player logged in as admin
    """

    def debugPrint(self, message):
        if self.debug == True:
            print(f"[DEBUG] [PlayerStatusHandler] {message}")

    def __init__(self, discordClient):
        self.configs = {} # Stores a configuration object for every tracked server
        self.pendingData = {} # Stores a list of messages for every tracked server to be posted
        self.lock = Lock()
        self.enabled = True
        self.task = None
        self.discordClient = discordClient
        self.debug = False
    
    def add_config(self, serverId, playerStatusConfig):
        with self.lock:
            self.configs[serverId] = playerStatusConfig
            self.pendingData[serverId] = []

    def get_config(self, serverId):
        with self.lock:
            return None if serverId not in self.configs else self.configs[serverId]

    def remove_config(self, serverId):
        with self.lock:
            del self.configs[serverId]
            del self.pendingData[serverId]

    async def track_server(self, serverId, interaction, title, icon, color):
        # TOOD: Status message about the server being tracked
        playerStatusConfig = PlayerStatusConfig(title, icon, color, interaction.channel)
        self.add_config(serverId, playerStatusConfig)

    ### Threading ###

    def start(self):
        if self.task is None:
            self.enabled = True
            self.task = asyncio.create_task(self.post_pending_messages())

    def stop(self):
        if self.task is not None:
            self.enabled = False

    async def wait_for_completion(self):
        counter = 0
        while counter < 70 and not self.task.done():
            await asyncio.sleep(1)
            counter += 1
        self.task = None

    ### Discord update ###

    async def post_pending_messages(self):
        while self.enabled == True:
            # Sleep 60 seconds, but abort at any time when requested
            for _ in range(1, 60):
                await asyncio.sleep(1)
                if self.enabled == False:
                    return
            self.debugPrint("Waking up")
            # Copy configs and pending data (keep the lock short)
            with self.lock:
                configsCopy = {serverId: self.configs[serverId] for serverId in self.configs}
                pendingDataCopy = {}
                for serverId in self.pendingData:
                    pendingDataCopy[serverId] = copy.deepcopy(self.pendingData[serverId])
                    self.pendingData[serverId] = []
            self.debugPrint("Copied data")
            # Process copied data now
            for serverId, config in configsCopy.items():
                if len(pendingDataCopy[serverId]) > 0:
                    self.debugPrint(f"Processing messages for server ID {serverId}")
                    data = pendingDataCopy[serverId]

                    # Create a new embed for each message
                    for entry in data:
                        overrideColor, indicator, statusPart = self.get_entry_dependent_settings(entry, config)

                        try:
                            message = f"{indicator} **{entry.player}** is {statusPart} on {config.icon} **{config.title}**"
                            embed = discord.Embed(description=message, color=int(overrideColor,16))
                            await config.channel.send(embed=embed)
                        except Exception:
                            print(f"[WARN ] [PlayerStatusHandler] Failed creating a player status embed: {traceback.format_exc()}",
                            flush=True)

                        # don't spam messages
                        await asyncio.sleep(1)

        print("[INFO ] [PlayerStatusHandler] PlayerStatusHandler was aborted", flush=True)

    def get_entry_dependent_settings(self, entry, config):
        if entry.isOnlineMessage:
            overrideColor = config.color
            indicator = "👤"
            statusPart = "now online"
        elif entry.isOfflineMessage:
            overrideColor = "992E22"
            indicator = "👋"
            statusPart = "no longer"
        elif entry.isAdminMessage:
            overrideColor = config.color
            indicator = "🎩"
            statusPart = "now an admin"
        return overrideColor, indicator, statusPart

    ### Event listeners ###
    
    def on_player_online(self, serverId, playerName):
        with self.lock:
            if serverId in self.pendingData:
                self.pendingData[serverId].append(PlayerStatusMessage(playerName, isOnlineMessage=True))
            
    def on_player_offline(self, serverId, playerName):
         with self.lock:
            if serverId in self.pendingData:
                self.pendingData[serverId].append(PlayerStatusMessage(playerName, isOfflineMessage=True))

    def on_player_admin(self, serverId, playerName):
        with self.lock:
            if serverId in self.pendingData:
                self.pendingData[serverId].append(PlayerStatusMessage(playerName, isAdminMessage=True))
