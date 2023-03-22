from threading import Lock
import asyncio
import discord
import datetime
import traceback
import copy


class InfoPanelConfig:
    """This class stores the fixed information about an info panel which doesn't change for a server usually."""

    def __init__(self, ip, port, icon, title, channel, embed, color):
        self.ip = ip
        self.port = port
        self.icon = icon
        self.title = title
        self.color = color
        self.channel = channel
        self.embed = embed


class InfoPanelHandler:
    """This class is responsible for updating the info panel in the configured discord channel"""

    def debugPrint(self, message):
        if self.debug == True:
            print(f"[DEBUG] [InfoPanelHandler] {message}")

    def __init__(self, discordClient):
        self.configs = {}           # Stores the info panel configurations for each server ID
        # Stores the current data which needs to be published for each server ID
        self.pendingServerData = {}
        self.lock = Lock()
        self.enabled = True
        self.task = None
        self.discordClient = discordClient
        self.debug = True

    def add_config(self, serverId, discordInfoPanelConfig):
        with self.lock:
            self.configs[serverId] = discordInfoPanelConfig
            self.pendingServerData[serverId] = None

    async def create_embed(self, serverId, interaction, ip, port, icon, title, color):
        embed = discord.Embed(title="Pending...", color=int(color, 16))
        message = await interaction.channel.send(embed=embed)
        panelInfoConfig = InfoPanelConfig(
            ip, port, icon, title, interaction.channel, message, color)
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
        self.debugPrint("Processing has started")
        while self.enabled == True:
            await asyncio.sleep(60)
            self.debugPrint("Waking up")
            with self.lock:
                configsCopy = {serverId: self.configs[serverId] for serverId in self.configs}
                pendingDataCopy = {}
                for serverId in self.pendingServerData:
                    pendingDataCopy[serverId] = copy.deepcopy(self.pendingServerData[serverId])
                    self.pendingServerData[serverId] = None
            self.debugPrint(f"Copied data: {len(configsCopy)} configs with {len(pendingDataCopy)} pending entries")
            for serverId, config in configsCopy.items():
                if serverId in pendingDataCopy and pendingDataCopy[serverId] is not None:
                    self.debugPrint(f"Found updated data for server ID {serverId}")
                    data = pendingDataCopy[serverId]
                    # Build the text to be displayed
                    try:
                        self.debugPrint("Retrieving text")
                        embedText = self.getText(config, data)
                    except Exception:
                        print(
                            f"[WARN ] [InfoPanelHandler] Failed creating embed text: {traceback.format_exc()}"
                        )
                        continue

                    # Update the embed
                    try:
                        self.debugPrint("Updating embed")
                        embed = discord.Embed(
                            title=f"{config.icon} {data.serverName}",
                            description=embedText,
                            color=int(config.color, 16),
                        )
                        self.debugPrint("Adding last update field")
                        embed.add_field(name="Last Update", value=f"{datetime.datetime.now()}")
                        self.debugPrint("Updating embed")
                        await config.embed.edit(embed=embed)
                    except Exception:
                        print(
                            f"[WARN ] [InfoPanelHandler] Could not update embed for server {config.title} (ID {serverId}): {traceback.format_exc()}"
                        )

                    # don't spam discord
                    await asyncio.sleep(1)

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
            if serverId not in self.pendingServerData:
                self.debugPrint(f"Adding pending data for server ID {serverId}")
            self.pendingServerData[serverId] = serverData

    def getText(self, serverConfig, serverData):
        message = (
            f"**Map: **{serverData.mapName}\r\n"
            + f"**Status: **{serverData.status}\r\n"
            + f"**Server Time: **{self.get_server_time(serverData)}\r\n"
            + f"**Mods Link: **{self.get_mods_link(serverConfig)}\r\n"
            + f"**Players Online: **{len(serverData.onlinePlayers)}/{serverData.maxPlayers}\r\n"
        ) + "**Players: **"

        if not serverData.onlinePlayers:
            message = f"{message}(none)"
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
        return f"http://{serverConfig.ip}:{serverConfig.port}/mods.html"
