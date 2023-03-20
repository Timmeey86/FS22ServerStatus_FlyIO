from threading import Lock
import asyncio
import discord
import datetime
import traceback
import copy


class InfoPanelConfig:
    """This class stores the fixed information about an info panel which doesn't change for a server usually."""

    def __init__(self, ip, port, icon, title, channelId, embedId, color):
        self.ip = ip
        self.port = port
        self.icon = icon
        self.title = title
        self.color = color
        self.channelId = channelId
        self.embedId = embedId


class InfoPanelHandler:
    """This class is responsible for updating the info panel in the configured discord channel"""

    def debugPrint(self, message):
        if self.debug == True:
            print("[DEBUG] [InfoPanelHandler] %s" % message)

    def __init__(self, discordClient):
        self.configs = {}           # Stores the info panel configurations for each server ID
        # Stores the current data which needs to be published for each server ID
        self.pendingServerData = {}
        self.lock = Lock()
        self.enabled = True
        self.task = None
        self.discordClient = discordClient
        self.debug = False

    def add_config(self, serverId, discordInfoPanelConfig):
        with self.lock:
            self.configs[serverId] = discordInfoPanelConfig
            self.pendingServerData[serverId] = None

    async def create_embed(self, serverId, interaction, ip, port, icon, title, color):
        embed = discord.Embed(title="Pending...", color=int(color, 16))
        message = await interaction.channel.send(embed=embed)
        panelInfoConfig = InfoPanelConfig(
            ip, port, icon, title, interaction.channel_id, message.id, color)
        self.add_config(serverId, panelInfoConfig)

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
            with self.lock:
                configsCopy = copy.deepcopy(self.configs)
                pendingDataCopy = {}
                for serverId in self.pendingServerData:
                    pendingDataCopy[serverId] = copy.deepcopy(self.pendingServerData[serverId])
                    self.pendingServerData[serverId] = None
            for serverId in configsCopy:
                if serverId in pendingDataCopy and pendingDataCopy[serverId] is not None:
                    self.debugPrint("Found updated data for server ID %s" % (serverId))
                    data = pendingDataCopy[serverId]
                    config = configsCopy[serverId]
                    
                    # Try finding the message for the embed
                    try:
                        self.debugPrint("Retrieving channel")
                        channel = self.discordClient.get_channel(config.channelId)                            
                        self.debugPrint("Fetching embed for channel %s and embed %s" % (config.channelId, config.embedId))
                        embedMessage = await channel.fetch_message(config.embedId)
                    except:
                        print("[wARN ] [InfoPanelHandler] WARN: Could not find embed for server %s (ID %s): %s" %
                                (config.title, serverId, traceback.format_exc()))
                        continue
                    # Build the text to be displayed
                    try:
                        self.debugPrint("Retrieving text")
                        embedText = self.getText(config, data)
                    except:
                        print("[WARN ] [InfoPanelHandler] Failed creating embed text: %s" % traceback.format_exc())
                        continue

                    # Update the embed
                    try:
                        self.debugPrint("Updating embed")
                        embed = discord.Embed(title="%s %s" % (config.icon, data.serverName),
                                            description=embedText,
                                            color=int(config.color, 16))
                        self.debugPrint("Adding last update field")
                        embed.add_field(name="Last Update",
                                        value="%s" % datetime.datetime.now())
                        self.debugPrint("Updating embed")
                        await embedMessage.edit(embed=embed)
                    except:
                        print("[WARN ] [InfoPanelHandler] Could not update embed for server %s (ID %s): %s"
                        % (config.title, serverId, traceback.format_exc()))

        print("[INFO ] [InfoPanelHandler] InfoPanelHandler was aborted")
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
            "**Map: **" + serverData.mapName + "\r\n" + \
            "**Status: **" + str(serverData.status.value) + "\r\n" + \
            "**Server Time: **" + self.get_server_time(serverData) + "\r\n" + \
            "**Mods Link: **" + self.get_mods_link(serverConfig) + "\r\n" + \
            "**Players Online: **" + str(len(serverData.onlinePlayers)) + "/" + serverData.maxPlayers + "\r\n" + \
            "**Players: **"

        if not serverData.onlinePlayers:
            message = message + "(none)"
        else:
            for playerName in serverData.onlinePlayers:
                message = message + "\r\n - %s (%s min)" % (
                    playerName, serverData.onlinePlayers[playerName].onlineTime)

        return message

    def get_server_time(self, serverData):
        totalsec, _ = divmod(int(serverData.dayTime), 1000)
        totalmin, _ = divmod(totalsec, 60)
        hours, minutes = divmod(totalmin, 60)
        return f'{hours:02d}:{minutes:02d}'

    def get_mods_link(self, serverConfig):
        """Retrieves the link to the mods page"""
        return "http://%s:%s/mods.html" % (serverConfig.ip, serverConfig.port)
