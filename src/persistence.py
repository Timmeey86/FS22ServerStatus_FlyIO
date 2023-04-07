from discord.commandhandler import CommandHandler
from discord.infopanelhandler import InfoPanelConfig, InfoPanelHandler
from discord.playerstatushandler import PlayerStatusConfig, PlayerStatusHandler
from discord.serverstatushandler import ServerStatusConfig, ServerStatusHandler
from discord.summaryhandler import SummaryConfig, SummaryHandler
from fs22.fs22server import FS22ServerConfig
from stats.statstracker import OnlineTimeTracker
from stats.statsreporter import StatsReporter
from stats.playertracker import PlayerTracker
import json
import os
import traceback
import discord

def to_json(obj):
    return json.dumps(obj, default=lambda innerObj: getattr(innerObj, '__dict__', str(innerObj)))


class ServerConfiguration:
    """This class stores the bot configuration of a single FS22 server and anything related to it"""

    def __init__(self, guildId, ip, port, apiCode, icon, title, color):
        self.guildId = guildId
        self.ip = ip
        self.port = port
        self.apiCode = apiCode
        self.icon = icon
        self.title = title
        self.color = color
        self.infoChannelId = None
        self.infoEmbedId = None
        self.playerChannelId = None
        self.serverChannelId = None
        self.summaryShortName = None
        self.summaryChannelId = None
        self.botChannelId = None


class BotConfiguration:
    """This class stores the current configuration of the bot as a single object"""

    def __init__(self):
        self.serverConfigs = {}
        self.statsEmbedsAndChannels: dict[int, int] = {}

    def add_server_config(self, serverId, serverConfig):
        self.serverConfigs[serverId] = serverConfig


class PersistenceDataMapper:
    """This class is responsible for translating between the active handlers and the persistent storage"""

    def __init__(self, commandHandler, storageRootPath):
        self.commandHandler: CommandHandler = commandHandler
        self.storageRootPath = storageRootPath

    def get_config_folder(self):
        return os.path.join(self.storageRootPath, "fssb")

    def get_config_file(self, configFolder):
        return os.path.join(configFolder, "config.json")
    
    def get_timetracker_file(self, configFolder):
        return os.path.join(configFolder, "timetracking.json")
    
    def get_backup_file(self, configFOlder):
        return os.path.join(configFolder, "timetracking_backup.json")

    def store_data(self):
        jsonData = self.store_as_json()
        configFolder = self.get_config_folder()
        if not os.path.exists(configFolder):
            os.mkdir(configFolder)
        with open(self.get_config_file(configFolder), "w") as file:
            file.write(jsonData)

    async def get_tracking_data(self) -> str:
        configFolder = self.get_config_folder()
        timetrackerFilePath = self.get_timetracker_file(configFolder)
        try:            
            if os.path.exists(timetrackerFilePath):
                with open(timetrackerFilePath, "r") as file:
                    print(f"[INFO ] [Persistence] Loading time tracker data from {timetrackerFilePath}")
                    return file.read()
            else:
                print("[INFO ] [Persistence] No time tracker file found")
        except Exception:
            print(f"[WARN ] [Persistence] Failed restoring time tracker: {traceback.format_exc()}")
        
        return None

    async def restore_data(self, discordClient):
        trackingData = await self.get_tracking_data()
        if trackingData:
            print("[INFO ] [Persistence] Restoring time tracker from existing data")
            timetracker = OnlineTimeTracker.from_json(trackingData)
        else:
            print("[INFO ] [Persistence] Creating new time tracker")
            timetracker = OnlineTimeTracker.create_new()

        configFolder = self.get_config_folder()
        filePath=self.get_config_file(configFolder)
        if os.path.exists(filePath):
            with open(filePath, "r") as file:
                await self.restore_from_json(file.read(), discordClient, timetracker)

    def store_as_json(self):
        botConfiguration = BotConfiguration()
        fs22configs = self.commandHandler.get_configs()
        for serverId, fs22config in fs22configs.items():

            # Get base parameters
            serverConfig = ServerConfiguration(
                guildId=fs22config.guildId,
                ip=fs22config.ip,
                port=fs22config.port,
                apiCode=fs22config.apiCode,
                icon=fs22config.icon,
                title=fs22config.title,
                color=fs22config.color)

            # Get potential info channel config
            infoConfig = self.commandHandler.infoPanelHandler.get_config(
                serverId)
            if infoConfig is not None:
                serverConfig.infoChannelId = infoConfig.channel.id
                serverConfig.infoEmbedId = infoConfig.embed.id

            # Get potential player channel config
            playerConfig = self.commandHandler.playerStatusHandler.get_config(
                serverId)
            if playerConfig is not None:
                serverConfig.playerChannelId = playerConfig.channel.id

            # Get potential server channel config
            serverStatusConfig = self.commandHandler.serverStatusHandler.get_config(
                serverId)
            if serverStatusConfig is not None:
                serverConfig.serverChannelId = serverStatusConfig.channel.id

            # Get potential summary channel config
            summaryConfig = self.commandHandler.summaryHandler.get_config(
                serverId)
            if summaryConfig is not None:
                serverConfig.summaryChannelId = summaryConfig.channel.id
                serverConfig.summaryShortName = summaryConfig.shortName

            for embedMessage in self.commandHandler.statsReporter.embeds:
                botConfiguration.statsEmbedsAndChannels[embedMessage.id] = embedMessage.channel.id

            botConfiguration.add_server_config(serverId, serverConfig)

        return to_json(botConfiguration)

    def store_time_tracking_data(self, timeTrackingData):
        configFolder = self.get_config_folder()
        timeTrackerFilePath = self.get_timetracker_file(configFolder)
        backupFilePath = self.get_backup_file(configFolder)
        if self.commandHandler.playerTracker is not None:
            try:
                if os.path.exists(backupFilePath):
                    os.remove(backupFilePath)
                if os.path.exists(timeTrackerFilePath):
                    os.rename(timeTrackerFilePath, backupFilePath)
                print("[INFO ] [Persistence] Writing time tracking data")
                with open(self.get_timetracker_file(self.get_config_folder()), "w") as file:
                    file.write(timeTrackingData)
            except Exception:
                print(f"[WARN ] [Persistence] Failed writing time tracking data: {traceback.format_exc()}")
        
    async def restore_from_json(self, jsonString, discordClient, timetracker):
        print("[INFO ] [Persistence] Restoring config from JSON")
        data = json.loads(jsonString)

        serverConfigsDict = data["serverConfigs"]
        serverConfigs = {}
        for serverIdStr, serverConfigDict in serverConfigsDict.items():
            serverId = int(serverIdStr)

            # Restore main server config
            fs22serverConfig = FS22ServerConfig(
                id=serverId,
                ip=serverConfigDict["ip"],
                port=serverConfigDict["port"],
                apiCode=serverConfigDict["apiCode"],
                icon=serverConfigDict["icon"],
                title=serverConfigDict["title"],
                color=serverConfigDict["color"],
                guildId=serverConfigDict["guildId"])
            serverConfigs[serverId] = fs22serverConfig

        # Register the configs
        if timetracker is not None:
            playerTracker = PlayerTracker(timetracker)
            self.commandHandler.set_player_tracker(playerTracker)
            playerTracker.events.stats_updated += self.store_time_tracking_data
            self.commandHandler.statsReporter.set_time_tracker(timetracker)
        self.commandHandler.restore_servers(serverConfigs)

        # Now restore the settings for the individual handlers
        for serverIdStr, serverConfigDict in serverConfigsDict.items():
            serverId = int(serverIdStr)
            fs22serverConfig = serverConfigs[serverId]

            await self.restore_info_panel_handler(serverConfigDict, fs22serverConfig, discordClient)
            await self.restore_player_status_handler(serverConfigDict, fs22serverConfig, discordClient)
            await self.restore_server_status_handler(serverConfigDict, fs22serverConfig, discordClient)
            await self.restore_summary_handler(serverConfigDict, fs22serverConfig, discordClient)
            # TODO
            botChannelId = serverConfigDict["botChannelId"]

        # Restore stats reporter
        await self.restore_stats_embed(data.get("statsEmbedsAndChannels", {}), discordClient)

    async def restore_info_panel_handler(self, serverConfigDict, serverConfig, discordClient):
        """Restores the configuration for the InfoPanelHandler from the persistent storage."""

        infoChannelId = serverConfigDict["infoChannelId"]
        infoEmbedId = serverConfigDict["infoEmbedId"]

        if infoChannelId and infoEmbedId:
            try:
                infoChannel = await discordClient.fetch_channel(infoChannelId)
                infoEmbed = await infoChannel.fetch_message(infoEmbedId)
                self.commandHandler.infoPanelHandler.add_config(serverConfig.id, InfoPanelConfig(
                    ip=serverConfig.ip,
                    port=serverConfig.port,
                    icon=serverConfig.icon,
                    title=serverConfig.title,
                    color=serverConfig.color,
                    channel=infoChannel,
                    embed=infoEmbed))
                print(
                    f"[INFO ] [PersistenceDataMapper] Successfully restored info panel handler for server {serverConfig.id}")
            except Exception:
                print(
                    f"[WARN ] [PersistenceDataMapper] Failed restoring info channel: {traceback.format_exc()}")

    async def restore_player_status_handler(self, serverConfigDict, serverConfig, discordClient):
        """Restores the configuration for the PlayerStatusHandler from the persistent storage."""

        if playerChannelId := serverConfigDict["playerChannelId"]:
            try:
                playerChannel = await discordClient.fetch_channel(playerChannelId)
                self.commandHandler.playerStatusHandler.add_config(serverConfig.id, PlayerStatusConfig(
                    icon=serverConfig.icon,
                    title=serverConfig.title,
                    color=serverConfig.color,
                    channel=playerChannel))
                print(
                    f"[INFO ] [PersistenceDataMapper] Successfully restored player status handler for server {serverConfig.id}")
            except Exception:
                print(
                    f"[WARN ] [PersistenceDataMapper] Failed restoring player status handler: {traceback.format_exc()}")

    async def restore_server_status_handler(self, serverConfigDict, serverConfig, discordClient):
        """Restores the configuration for the ServerStatusHandler from the persistent storage."""

        if serverChannelId := serverConfigDict["serverChannelId"]:
            try:
                serverChannel = await discordClient.fetch_channel(serverChannelId)
                self.commandHandler.serverStatusHandler.add_config(serverConfig.id, ServerStatusConfig(
                    icon=serverConfig.icon,
                    title=serverConfig.title,
                    color=serverConfig.color,
                    channel=serverChannel))
                print(
                    f"[INFO ] [PersistenceDataMapper] Successfully restored server status handler for server {serverConfig.id}")
            except Exception:
                print(
                    f"[WARN ] [PersistenceDataMapper] Failed restoring server status handler: {traceback.format_exc()}")

    async def restore_summary_handler(self, serverConfigDict, serverConfig, discordClient):
        """Restores the configuration for the SummaryHandler from the persistent storage."""

        summaryShortName = serverConfigDict["summaryShortName"]
        summaryChannelId = serverConfigDict["summaryChannelId"]

        if summaryShortName and summaryChannelId:
            try:
                summaryChannel = await discordClient.fetch_channel(summaryChannelId)
                self.commandHandler.summaryHandler.add_config(serverConfig.id, SummaryConfig(
                    shortName=summaryShortName,
                    channel=summaryChannel))
                print(
                    f"[INFO ] [PersistenceDataMapper] Successfully restored summary handler for server {serverConfig.id}")
            except Exception:
                print(
                    f"[WARN ] [PersistenceDataMapper] Failed restoring summary handler: {traceback.format_exc()}")

    async def restore_stats_embed(self, embedData: dict[str, int], discordClient: discord.Client):
        """Restores a single embed for player stats form the persistent storage."""

        embeds = []
        for embedIdStr, channelId in embedData.items():
            try:
                statsChannel = await discordClient.fetch_channel(channelId)
                embedMessage = await statsChannel.fetch_message(int(embedIdStr))
                embeds.append(embedMessage)
                print("[INFO] [PersistenceDataMapper] Successfully restored stats embed")
            except Exception:
                print(f"[WARN ] [PersistenceDataMapper] Failed restoring stats embed: {traceback.format_exc()}")

        self.commandHandler.statsReporter.restore_embeds(embeds)
            