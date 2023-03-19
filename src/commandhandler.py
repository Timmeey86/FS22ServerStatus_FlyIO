from threading import Lock

class CommandHandler:

    def __init__(self):
        self.lock = Lock()

    def update_servers(self, serverConfigs):
        with self.lock:
            self.serverConfigs = serverConfigs

    async def add_embed(self, interaction, id, flag, title, color):

        if not interaction.permissions.administrator:
            await interaction.response.send_message(
                    content="Only administrators are allowed to run commands on this bot",
                    ephemeral=True,
                    delete_after=10)
            return

        with self.lock:
            if id not in self.serverConfigs:
                await interaction.response.send_message(
                    content="There is no server with ID %s" % id,
                    ephemeral=True,
                    delete_after=10
                    )
