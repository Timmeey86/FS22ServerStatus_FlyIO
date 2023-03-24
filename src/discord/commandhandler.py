from threading import Lock
from fs22.fs22server import FS22ServerConfig
from fs22.servertracker import ServerTracker
from discord.infopanelhandler import InfoPanelHandler
from discord.playerstatushandler import PlayerStatusHandler
from discord.serverstatushandler import ServerStatusHandler
from discord.summaryhandler import SummaryHandler
import traceback


class CommandHandler:

    def __init__(self, infoPanelHandler, playerStatusHandler, serverStatusHandler, summaryHandler):
        self.lock = Lock()
        self.serverConfigs = {}
        self.serverTrackers = {}
        self.nextServerId = 0
        self.infoPanelHandler = infoPanelHandler
        self.playerStatusHandler = playerStatusHandler
        self.serverStatusHandler = serverStatusHandler
        self.summaryHandler = summaryHandler

    def restore_servers(self, serverConfigs):
        with self.lock:
            self.serverConfigs = serverConfigs
            for id, serverConfig in serverConfigs.items():
                if (id >= self.nextServerId):
                    self.nextServerId = id + 1
                self.add_tracker(serverConfig)

    def get_configs(self):
        with self.lock:
            return {serverId: self.serverConfigs[serverId] for serverId in self.serverConfigs}

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
                    content=f"There is no server with ID {serverId}",
                    ephemeral=True,
                    delete_after=10,
                )
                for serverId in self.serverConfigs:
                    print(f"Available server ID: {serverId}")
                return False

            print("[CommandHandler] Server found")

            if str(self.serverConfigs[serverId].guildId) != str(interaction.guild_id):
                await interaction.response.send_message(
                    content="You can only modify a server from the same discord guild where you created it. " +
                            "Did you supply the wrong server ID?",
                    ephemeral=True,
                    delete_after=10
                )
                print(
                    f"Stored guild ID: {str(self.serverConfigs[serverId].guildId)}. Supplied guild ID: {str(interaction.guild_id)}"
                )
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
        except Exception:
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
        except Exception:
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
        except Exception:
            await interaction.response.send_message(content="Failed tracking server status")
            print(traceback.format_exc())

    async def set_summary_channel(self, interaction, id, shortName):
        if not await self.check_parameters(interaction, id):
            return
        with self.lock:
            config = self.serverConfigs[id]
        try:
            await self.summaryHandler.track_server(id, interaction, shortName)
            await interaction.response.send_message(content="Summary successfully registered on current channel", ephemeral=True, delete_after=10)
        except Exception:
            await interaction.response.send_message(content="Failed setting up summary channel")
            print(traceback.format_exc())

    async def set_bot_status_channel(self, interaction):
        if not await self.check_parameters(interaction, id):
            return

    async def register_server(self, interaction, ip, port, apiCode, icon, title, color):
        if not await self.check_admin_permission(interaction):
            return
        with self.lock:
            serverId = self.nextServerId
            self.nextServerId += 1
            serverConfig = FS22ServerConfig(
                serverId, ip, port, apiCode, icon, title, color, interaction.guild_id)
            self.serverConfigs[serverId] = serverConfig
            self.add_tracker(serverConfig)
        await interaction.response.send_message(content=f"Successfully registered the server. Your server ID for {title} ({ip}:{port}) is {serverId}. " +
                                                "Please write that down (or pin this message if in an admin-only channel), " +
                                                "since you will need it for all further commands")


    async def remove_server(self, interaction, id):
        if not await self.check_parameters(interaction, id):
            return
        with self.lock:
            self.remove_tracker(id)
            self.infoPanelHandler.remove_config(id)
            self.playerStatusHandler.remove_config(id)
            self.serverStatusHandler.remove_config(id)
            self.summaryHandler.remove_config(id)
            del self.serverConfigs[id]
        await interaction.response.send_message(content=f"Successfully removed server with ID {id}", ephemeral=True)

    def add_tracker(self, serverConfig):
        tracker = ServerTracker(serverConfig)
        tracker.events.initial += self.infoPanelHandler.on_initial_event
        tracker.events.updated += self.infoPanelHandler.on_updated
        tracker.events.updated += self.summaryHandler.on_updated
        tracker.events.playerWentOnline += self.playerStatusHandler.on_player_online
        tracker.events.playerWentOffline += self.playerStatusHandler.on_player_offline
        tracker.events.playerAdminStateChanged += self.playerStatusHandler.on_player_admin
        tracker.events.serverStatusChanged += self.serverStatusHandler.on_server_status_changed
        tracker.start_tracker()
        self.serverTrackers[serverConfig.id] = tracker

    def remove_tracker(self, id):
        if id in self.serverTrackers:
            self.serverTrackers[id].stop_tracker()
            del self.serverTrackers[id]