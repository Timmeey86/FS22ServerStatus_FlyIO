from discord.commandhandler import CommandHandler
from discord.infopanelhandler import InfoPanelConfig, InfoPanelHandler
from discord.playerstatushandler import PlayerStatusConfig, PlayerStatusHandler
from discord.serverstatushandler import ServerStatusConfig, ServerStatusHandler
from discord.summaryhandler import SummaryConfig, SummaryHandler
from fs22.fs22server import FS22ServerConfig


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

    def add_server_config(self, serverId, serverConfig):
        self.serverConfigs[serverId] = serverConfig


class PersistenceDataMapper:
    """This class is responsible for translating between the active handlers and the persistent storage"""

    def __init__(self, commandHandler):
        self.commandHandler = commandHandler

    def get_current_data(self):
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
            infoConfig = self.commandHandler.infoPanelHandler.get_config(serverId)
            if infoConfig is not None:
                serverConfig.infoChannelId = infoConfig.channel.id
                serverConfig.infoEmbedId = infoConfig.embed.id

            # Get potential player channel config
            playerConfig = self.commandHandler.playerStatusHandler.get_config(serverId)
            if playerConfig is not None:
                serverConfig.playerChannelId = playerConfig.channel.id

            # Get potential server channel config
            serverStatusConfig = self.commandHandler.serverStatusHandler.get_config(serverId)
            if serverStatusConfig is not None:
                serverConfig.serverChannelId = serverStatusConfig.channel.id

            # Get potential summary channel config
            summaryConfig = self.commandHandler.summaryHandler.get_config(serverId)
            if summaryConfig is not None:
                serverConfig.summaryChannelId = summaryConfig.channel.id
                serverConfig.summaryShortName = summaryConfig.shortName

            botConfiguration.add_server_config(serverId, serverConfig)
            
        return botConfiguration

# TODO: Serialization, Deserialization, Channel/Embed retrieval
# TODO: Retrieve parameters from command handler
# TODO: Restore parameters to command handler
# TODO: Auto-save after changes
# TODO: Restore before tracking servers
