import asyncio
from fs22server import FS22ServerConfig
from servertracker import ServerTracker
from infopanelhandler import InfoPanelConfig, InfoPanelHandler
from commandhandler import CommandHandler
from dotenv import load_dotenv
import discord
from discord import app_commands
import os
import signal
import sys
import traceback

stopped = False

# Create a discord client to allow interacting with a discord server
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
commandHandler = CommandHandler()

#Allows adding a server embed to an already registered server
@tree.command(name="fssb_add_embed",
              description="Adds an embed for a new server to this channel")
@app_commands.describe(
  id="The ID of the server",
  flag="The flag to display (copy a flag emoji in here)",
  title="The title of the server",
  color="The color code which identifies the server, like 992D22")
async def fssb_add_embed(interaction, id: int, flag: str, title: str, color: str):
    await commandHandler.add_embed(interaction, id, flag, title, color)

@tree.command(name="fssb_good_morning", description="Says good morning")
@app_commands.describe()
async def fssb_good_morning(interaction):    
    if not interaction.permissions.administrator:
        await interaction.response.send_message(
                content="Only administrators are allowed to run commands on this bot",
                ephemeral=True,
                delete_after=10)
        return
    await interaction.channel.send("Good morning, farmers")
    await interaction.response.send_message(
        content="Done", 
        ephemeral=True,
        delete_after=10)

"""
def initial(serverId, serverData):
    print("[main] Received initial event for server %s" % (serverId))


def updated(serverId, serverData):
    # print("[main]Received update event for server %s" % (serverId, serverData.__dict__))
    pass


def playerWentOnline(serverId, playerName):
    print("[main] Player %s joined server %s" % (playerName, serverId))


def playerWentOffline(serverId, playerName):
    print("[main] Player %s logged out from server %s" % (playerName, serverId))


def serverStatusChanged(serverId, serverData):
    print("[main] Server %s is now %s" % (serverId, serverData.status.name))


def playerAdminStateChanged(serverId, playerName):
    print("[main] Player %s is now an admin" % (playerName))
"""

@client.event
async def on_ready():
    """
    Tells us when the bot is logged in to discord (in the replit console)
    """
    # Enable slash commands like /fss_add_embed
    print("[main] Discord client is ready")
    print("[main] Waiting for tree sync")
    await tree.sync()
    print("[main] Tree is now synched")

    if os.path.exists("/data"):
        print("[main] /data exists")
    if os.path.exists("C:/temp"):
        print("[main] C:\\temp exists")

    serverA = FS22ServerConfig(0, os.getenv("SERVER_A_IP"), os.getenv(
        "SERVER_A_PORT"), os.getenv("SERVER_A_APICODE"))
    serverB = FS22ServerConfig(1, os.getenv("SERVER_B_IP"), os.getenv(
        "SERVER_B_PORT"), os.getenv("SERVER_B_APICODE"))
    serverC = FS22ServerConfig(2, os.getenv("SERVER_C_IP"), os.getenv(
        "SERVER_C_PORT"), os.getenv("SERVER_C_APICODE"))
    serverD = FS22ServerConfig(3, os.getenv("SERVER_D_IP"), os.getenv(
        "SERVER_D_PORT"), os.getenv("SERVER_D_APICODE"))

    serverConfigs = {}
    serverConfigs[0] = serverA
    serverConfigs[1] = serverB
    serverConfigs[2] = serverC
    serverConfigs[3] = serverD
    commandHandler.update_servers(serverConfigs)

    testConfig = InfoPanelConfig(os.getenv("SERVER_C_IP"), os.getenv("SERVER_C_PORT"), "tmp", "tmpTitle", "0", "1", "2", "blue")
    testHandler = InfoPanelHandler()
    testHandler.add_config(2, testConfig)

    for serverId in serverConfigs:
        serverConfig = serverConfigs[serverId]
        tracker = ServerTracker(serverConfig)
        #tracker.events.initial += initial
        tracker.events.initial += testHandler.on_initial_event
        #tracker.events.updated += updated
        tracker.events.updated += testHandler.on_updated
        #tracker.events.playerWentOnline += playerWentOnline
        #tracker.events.playerWentOffline += playerWentOffline
        #tracker.events.serverStatusChanged += serverStatusChanged
        #tracker.events.playerAdminStateChanged += playerAdminStateChanged
        tracker.start_tracker()

    print("[main] Finished initialization")
    testHandler.start()

    while (not stopped):
        print("[main] Sleeping 60s", flush=True)
        await asyncio.sleep(60)

    print("[main] Waiting for threads to end")
    testHandler.stop()
    print("[main] Done")


def signal_handler(sig, frame):
    print("[main] Caught Ctrl+C. Stopping")
    stopped = True
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
try:

    if os.getenv("SERVER_A_IP") is None:
        print("[main] Loading local environment")
        load_dotenv()
    else:
        print("[main] Using existing environment")

    print("[main] Running client")
    token = os.getenv("DISCORD_TOKEN")
    client.run(token)
except:
    print("[main] %s" % traceback.format_exc())
