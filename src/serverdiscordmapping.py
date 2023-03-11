from fs22server import FS22ServerConfig

class DiscordMemberLogChannelConfig:
    """Stores the configuration of the channel in discord which shall receive member online/offline/admin messages"""

    def __init__(self, channelId, serverColor, flag):
        self.channelId = channelId
        self.serverColor = serverColor
        self.flag = flag

class DiscordServerLogChannelConfig:
    """Stores the configuration of the channel in discord which shall receive server online/offline messages"""

    def __init__(self, channelId, serverColor, flag):
        self.channelId = channelId
        self.serverColor = serverColor
        self.flag = flag

class DiscordVoiceChannelConfig:
    """Stores the configuration of the voice channel in discord which shall display the server state and the amount of online players"""

    def __init__(self, channelId, serverShortName):
        self.channelId = channelId
        self.serverShortName = serverShortName

class FS22ServerToDiscordMapping:
    """Provides mapping between an FS22 server and the associated discord channels"""

    def __init__(self, fs22ServerConfig, discordGuildId):
        self.serverConfig = fs22ServerConfig
        self.discordStatusPanelConfig = None
        self.discordMemberLogChannelConfig = None
        self.discordServerLogChannelConfig = None
        self.discordVoiceChannelConfig = None
        self.discordGuildId = discordGuildId