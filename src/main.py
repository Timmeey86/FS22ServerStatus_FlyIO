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


# build the main object tree
infoPanelHandler = InfoPanelHandler(client)
commandHandler = CommandHandler(infoPanelHandler)


@tree.command(name="fssb_add_embed",
              description="Adds an embed to this channel displaying live info about the FS22 server")
@app_commands.describe(
    id="The ID of the server")
async def fssb_add_embed(interaction, id: int):
    print("Received fssb_add_embed command for id %s" % id)
    await commandHandler.add_embed(interaction, id)


@tree.command(name="fssb_set_member_channel",
              description="Sets this channel as the target channel for online/offline/admin player messages")
@app_commands.describe(
    id="The ID of the server")
async def fssb_set_member_channel(interaction, id: int):
    await commandHandler.set_member_channel(interaction, id)


@tree.command(name="fssb_set_server_channel",
              description="Sets this channel as the target channel for online/offline server messages")
@app_commands.describe(id="The ID of the server")
async def fssb_set_server_channel(interaction, id: int):
    await commandHandler.set_server_channel(interaction, id)


@tree.command(name="fssb_set_status_channel",
              description="Make this channel display the online state and player count in its name")
@app_commands.describe(id="The ID of the server", shortname="The short name for the server")
async def fssb_set_status_channel(interaction, id: int, shortname: str):
    await commandHandler.set_status_channel(interaction, id, shortname)


@tree.command(name="fssb_set_bot_status_channel",
              description="Make this channel display status messages concerning the bot")
@app_commands.describe()
async def fssb_set_bot_status_channel(interaction):
    await commandHandler.set_bot_status_channel(interaction)


@tree.command(name="fssb_register_server",
              description="Register an FS22 server to be tracked by this bot. Required for other commands")
@app_commands.describe(
    ip="The IP address or hostname of the FS22 server (the game server, not the server host)",
    port="The port to access the server on",
    apicode="The API code required for accessing the FS22 status XML file",
    icon="The Icon to be displayed (e.g. a flag like :flag_uk:)",
    title="The title of the server (anything you like)",
    color="The color code to be used in various messages, e.g. FF0000 for red (RGB Hex)")
async def fssb_register_server(interaction, ip: str, port: str, apicode: str, icon: str, title: str, color: str):
    await commandHandler.register_server(interaction, ip, port, apicode, icon, title, color)

@tree.command(name="fssb_remove_server",
              description="Stops tracking an FS22 server")
@app_commands.describe(id="The server ID")
async def fssb_remove_server(interaction, id: int):
    await commandHandler.remove_server(interaction, id)

@tree.command(name="fssb_send_message", description="Makes the bot send a message for you")
@app_commands.describe(message="The message you would like to send")
async def fssb_send_message(interaction, message: str):
    if not interaction.permissions.administrator:
        await interaction.response.send_message(
            content="Only administrators are allowed to run commands on this bot",
            ephemeral=True,
            delete_after=10)
        return
    await interaction.channel.send(message)
    await interaction.response.send_message(
        content="Done",
        ephemeral=True,
        delete_after=1)

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
    try:
        await tree.sync()
        print("[main] Tree is now synched")
    except:
        print("[main] Failed waiting for tree sync: %s" % traceback.format_exc())

    if os.path.exists("/data"):
        print("[main] /data exists")
    if os.path.exists("C:/temp"):
        print("[main] C:\\temp exists")

    serverA = FS22ServerConfig(0, os.getenv("SERVER_A_IP"), os.getenv(
        "SERVER_A_PORT"), os.getenv("SERVER_A_APICODE"), "🇬🇧", "Server A", "206694", "726322101786509335")
    serverB = FS22ServerConfig(1, os.getenv("SERVER_B_IP"), os.getenv(
        "SERVER_B_PORT"), os.getenv("SERVER_B_APICODE"), "🇵🇱", "Server B", "FFFF00", "726322101786509335")
    serverC = FS22ServerConfig(2, os.getenv("SERVER_C_IP"), os.getenv(
        "SERVER_C_PORT"), os.getenv("SERVER_C_APICODE"), "🇩🇪", "Server C", "57F288", "726322101786509335")
    serverD = FS22ServerConfig(3, os.getenv("SERVER_D_IP"), os.getenv(
        "SERVER_D_PORT"), os.getenv("SERVER_D_APICODE"), "🇮🇹", "Server D", "9C59B6", "726322101786509335")

    serverConfigs = {}
    serverConfigs[0] = serverA
    serverConfigs[1] = serverB
    serverConfigs[2] = serverC
    serverConfigs[3] = serverD
    commandHandler.restore_servers(serverConfigs)

    for serverId in serverConfigs:
        serverConfig = serverConfigs[serverId]
        tracker = ServerTracker(serverConfig)
        # tracker.events.initial += initial
        tracker.events.initial += infoPanelHandler.on_initial_event
        # tracker.events.updated += updated
        tracker.events.updated += infoPanelHandler.on_updated
        # tracker.events.playerWentOnline += playerWentOnline
        # tracker.events.playerWentOffline += playerWentOffline
        # tracker.events.serverStatusChanged += serverStatusChanged
        # tracker.events.playerAdminStateChanged += playerAdminStateChanged
        tracker.start_tracker()

    print("[main] Finished initialization")
    infoPanelHandler.start()

    while (not stopped):
        print("[main] Sleeping 5s", flush=True)
        await asyncio.sleep(5)

    print("[main] Waiting for threads to end")
    infoPanelHandler.stop()
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
