from threading import Lock


class CommandHandler:

    def __init__(self):
        self.lock = Lock()
        self.serverConfigs = {}
        self.nextServerId = 0

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

    async def check_parameters(self, interaction, serverId):
        """
        Checks if 
        - the user has the required permissions, 
        - the given server is known
        - the command was sent from the same discord guild which added the server
        """
        if not await check_admin_permission(interaction):
            return False

        with self.lock:
            if serverId not in self.serverConfigs:
                await interaction.response.send_message(
                    content="There is no server with ID %s" % serverId,
                    ephemeral=True,
                    delete_after=10
                )
                return False

            if self.serverConfigs[serverId].guildId != interaction.guild_id:
                await interaction.response.send_message(
                    content="You can only modify a server from the same discord guild where you created it. " +
                            "Did you supply the wrong server ID?",
                    ephemeral=True,
                    delete_after=10
                )
                return False
        return True

    async def add_embed(self, interaction, id):
        if not await check_parameters(interaction, id):
            return
        pass

    async def set_member_channel(self, interaction, id):
        if not await check_parameters(interaction, id):
            return
        pass

    async def set_server_channel(self, interaction, id):
        if not await check_parameters(interaction, id):
            return
        pass

    async def set_status_channel(self, interaction, id, shortName):
        if not await check_parameters(interaction, id):
            return
        pass

    async def set_bot_status_channel(self, interaction):
        if not await check_parameters(interaction, id):
            return
        pass

    async def register_server(interaction, ip, port, apiCode, icon, title, color):
        if not await check_admin_permission(interaction):
            return
        pass

    async def remove_server(interaction, id):
        if not await check_parameters(interaction, id):
            return
        pass
