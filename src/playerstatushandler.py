from threading import Lock
import asyncio
import discord
import traceback
import copy

class PlayerStatusConfig:
    """This class sores the fixed information about a player status reporting channel"""

    def __init__(self, title, icon, color, channelId):
        self.title = title
        self.icon = icon
        self.color = color
        self.channelId = channelId

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
            print("[DEBUG] [PlayerStatusHandler] %s" % message)

    def __init__(self, discordClient):
        self.configs = {} # Stores a configuration object for every tracked server
        self.pendingData = {} # Stores a list of messages for every tracked server to be posted
        self.lock = Lock()
        self.enabled = True
        self.task = None
        self.discordClient = discordClient
        self.debug = True
    
    def add_config(self, serverId, playerStatusConfig):
        with self.lock:
            self.configs[serverId] = playerStatusConfig
            self.pendingData[serverId] = []

    async def track_server(self, serverId, interaction, title, icon, color):
        # TOOD: Status message about the server being tracked
        playerStatusConfig = PlayerStatusConfig(title, icon, color, interaction.channel_id)
        self.add_config(serverId, playerStatusConfig)

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
            await asyncio.sleep(10)
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
                        channel = client.get_channel(config.channelId)
                    except:
                        # This could e.g. happen in case of Cloudflare rate limiting
                        print("[WARN ] [PlayerStatusHandler] Failed to retrieve member log channel ID: %s" % traceback.format_exc())
                        continue

                    # Create a new embed for each message
                    for entry in data:
                        if entry.isOnlineMessage:
                            overrideColor = config.color
                            indicator = "👤"
                            statusPart = "now online"
                        elif entry.isOfflineMessage:
                            overrideColor = "992E22"
                            indicator = "👋"
                            statusPart = "now offline"
                        elif entry.isAdminMessage:
                            overrideCOlor = config.color
                            indicator = "🎩"
                            statusPart = "now an admin"

                        try:
                            message = "%s **%s** is %s on %s **%s**" % (indicator, entry.player, statusPart, config.icon, config.title)
                            embed = discord.Embed(
                                description="🎩 **%s** is now an admin on **%s**" %
                                (playerStatus.playerName, serverData.name),
                                color=color)
                            await channel.send(embed=embed)
                        except:
                            print("[WARN ] [PlayerStatusHandler] Failed creating a player status embed: %s" % traceback.format_exc())

                        # don't spam messages
                        await asyncio.sleep(1)

        print("[INFO ] [PlayerStatusHandler] PlayerStatusHandler was aborted")
        self.task = None

    ### Event listeners ###
    
    def on_player_online(self, serverId, playerName):
        with self.lock:
            if serverId in self.pendingData:
                self.debugPrint("Player %s signed onto %s" % (playerName, serverId))
                self.pendingData[serverId].append(PlayerStatusMessage(playerName, isOnlineMessage=true))
            else:
                self.debugPrint("Skipping logged on player for server %s" % serverId)

    def on_player_offline(self, serverId, playerName):
         with self.lock:
            if serverId in self.pendingData:
                self.pendingData[serverId].append(PlayerStatusMessage(playerName, isOfflineMessage==true))

    def on_player_admin(self, serverId, playerName):
        with self.lock:
            if serverId in self.pendingData:
                self.pendingData[serverId].append(PlayerStatusMessage(playerName, isAdminMessage==true))
