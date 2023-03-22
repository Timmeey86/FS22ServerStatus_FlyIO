from threading import Lock
from fs22.fs22server import FS22ServerConfig
from discord.infopanelhandler import InfoPanelHandler
from discord.playerstatushandler import PlayerStatusHandler
from discord.serverstatushandler import ServerStatusHandler
import traceback

class CommandHandler:

    def __init__(self, infoPanelHandler, playerStatusHandler, serverStatusHandler):
        self.lock = Lock()
        self.serverConfigs = {}
        self.nextServerId = 0
        self.infoPanelHandler = infoPanelHandler
        self.playerStatusHandler = playerStatusHandler
        self.serverStatusHandler = serverStatusHandler

    def restore_servers(self, serverConfigs):
        with self.lock:
            self.serverConfigs = serverConfigs
            for id in serverConfigs:
                if(id >= self.nextServerId):
                    self.nextServerId = id + 1

    async def check_admin_permission(self, interaction):
        """
        Checks if the user has admin permissions
        """
        if not interaction.permissions.administrator:
            await interaction.response.send_message(
                content="Only administrators are allowed to run commands on this bot",
                ephemeral=True,
                delete_after=10)
            return False
        return True

    async def check_parameters(self, interaction, serverId):
        """
        Checks if 
        - the user has the required permissions, 
        - the given server is known
        - the command was sent from the same discord guild which added the server
        """
        if not await self.check_admin_permission(interaction):
            return False

        print("[CommandHandler] Permission granted")
        with self.lock:
            if serverId not in self.serverConfigs:
                await interaction.response.send_message(
                    content="There is no server with ID %s" % serverId,
                    ephemeral=True,
                    delete_after=10
                )
                for serverId in self.serverConfigs:
                    print("Available server ID: %s" % serverId)
                return False

            print("[CommandHandler] Server found")

            if str(self.serverConfigs[serverId].guildId) != str(interaction.guild_id):
                await interaction.response.send_message(
                    content="You can only modify a server from the same discord guild where you created it. " +
                            "Did you supply the wrong server ID?",
                    ephemeral=True,
                    delete_after=10
                )
                print("Stored guild ID: %s. Supplied guild ID: %s" % (str(self.serverConfigs[serverId].guildId), str(interaction.guild_id)))
                return False

            print("[CommandHandler] Guild matched")
        return True

    async def add_embed(self, interaction, id):
        if not await self.check_parameters(interaction, id):
            return
        with self.lock:
            config = self.serverConfigs[id]
        try:
            await self.infoPanelHandler.create_embed(id, interaction, config.ip, config.port, config.icon, config.title, config.color)
            await interaction.response.send_message(content="Panel successfully created", ephemeral=True, delete_after=10)
        except:
            await interaction.response.send_message(content="Failed creating the embed")
            print(traceback.format_exc())

    async def set_member_channel(self, interaction, id):
        if not await self.check_parameters(interaction, id):
            return
        with self.lock:
            config = self.serverConfigs[id]
        try:
            await self.playerStatusHandler.track_server(id, interaction, config.title, config.icon, config.color) 
            await interaction.response.send_message(content="Player status successfully tracked", ephemeral=True, delete_after=10)
        except:
            await interaction.response.send_message(content="Failed tracking player status")
            print(traceback.format_exc())

    async def set_server_channel(self, interaction, id):
        if not await self.check_parameters(interaction, id):
            return
        with self.lock:
            config = self.serverConfigs[id]
        try:
            await self.serverStatusHandler.track_server(id, interaction, config.title, config.icon, config.color)
            await interaction.response.send_message(content="Server status successfully tracked", ephemeral=True, delete_after=10)
        except:
            await interaction.response.send_message(content="Failed tracking server status")
            print(traceback.format_exc())
    
    async def set_status_channel(self, interaction, id, shortName):
        if not await self.check_parameters(interaction, id):
            return
        pass

    async def set_bot_status_channel(self, interaction):
        if not await self.check_parameters(interaction, id):
            return
        pass

    async def register_server(interaction, ip, port, apiCode, icon, title, color):
        if not await self.check_admin_permission(interaction):
            return
        with self.lock:
            serverId = self.nextServerId
            self.nextServerId += 1
            serverConfig = FS22ServerConfig(serverId, ip, port, apiCode, icon, title, color, interaction.guild_id)
            self.serverConfigs[serverId] = serverConfig
        await interaction.response.send_message(content="Successfully registered the server. Your server ID is %s. " +
        "Please write that down since you will need it for all further commands", ephemeral=True)
        # TODO: Connect events

    async def remove_server(interaction, id):
        if not await self.check_parameters(interaction, id):
            return
        pass
