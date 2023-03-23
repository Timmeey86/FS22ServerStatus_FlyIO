import asyncio
from fs22.fs22server import FS22ServerConfig
from fs22.servertracker import ServerTracker
from discord.infopanelhandler import InfoPanelHandler
from discord.playerstatushandler import PlayerStatusHandler
from discord.serverstatushandler import ServerStatusHandler
from discord.summaryhandler import SummaryHandler
from discord.commandhandler import CommandHandler
from persistence import PersistenceDataMapper
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
playerStatusHandler = PlayerStatusHandler(client)
serverStatusHandler = ServerStatusHandler(client)
summaryHandler = SummaryHandler(client)
commandHandler = CommandHandler(infoPanelHandler, playerStatusHandler, serverStatusHandler, summaryHandler)


@tree.command(name="fssb_add_embed",
              description="Adds an embed to this channel displaying live info about the FS22 server")
@app_commands.describe(
    id="The ID of the server")
async def fssb_add_embed(interaction, id: int):
    print(f"Received fssb_add_embed command for id {id}")
    await commandHandler.add_embed(interaction, id)
    print(PersistenceDataMapper(commandHandler).get_current_data().__dict__)


@tree.command(name="fssb_set_member_status_channel",
              description="Sets this channel as the target channel for online/offline/admin player messages")
@app_commands.describe(
    id="The ID of the server")
async def fssb_set_member_channel(interaction, id: int):
    await commandHandler.set_member_channel(interaction, id)
    print(PersistenceDataMapper(commandHandler).get_current_data().__dict__)


@tree.command(name="fssb_set_server_status_channel",
              description="Sets this channel as the target channel for online/offline server messages")
@app_commands.describe(id="The ID of the server")
async def fssb_set_server_channel(interaction, id: int):
    await commandHandler.set_server_channel(interaction, id)
    print(PersistenceDataMapper(commandHandler).get_current_data().__dict__)


@tree.command(name="fssb_set_summary_channel",
              description="Make this channel display the online state and player count in its name")
@app_commands.describe(id="The ID of the server", shortname="The short name for the server")
async def fssb_set_summary_channel(interaction, id: int, shortname: str):
    await commandHandler.set_summary_channel(interaction, id, shortname)
    print(PersistenceDataMapper(commandHandler).get_current_data().__dict__)


@tree.command(name="fssb_set_bot_status_channel",
              description="Make this channel display status messages concerning the bot")
@app_commands.describe()
async def fssb_set_bot_status_channel(interaction):
    await commandHandler.set_bot_status_channel(interaction)
    print(PersistenceDataMapper(commandHandler).get_current_data().__dict__)


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
    print(PersistenceDataMapper(commandHandler).get_current_data().__dict__)

@tree.command(name="fssb_remove_server",
              description="Stops tracking an FS22 server")
@app_commands.describe(id="The server ID")
async def fssb_remove_server(interaction, id: int):
    await commandHandler.remove_server(interaction, id)
    print(PersistenceDataMapper(commandHandler).get_current_data().__dict__)

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

@client.event
async def on_ready():
    """
    Tells us when the bot is logged in to discord (in the replit console)
    """
    # Enable slash commands like /fss_add_embed
    print("[INFO ] [main] Discord client is ready")
    print("[INFO ] [main] Waiting for tree sync")
    try:
        await tree.sync()
        print("[INFO ] [main] Tree is now synched")
    except Exception:
        print(f"[INFO ] [main] Failed waiting for tree sync: {traceback.format_exc()}")

    if os.path.exists("/data"):
        print("[INFO ] [main] /data exists")
    if os.path.exists("C:/temp"):
        print("[INFO ] [main] C:\\temp exists")

    serverA = FS22ServerConfig(0, os.getenv("SERVER_A_IP"), os.getenv(
        "SERVER_A_PORT"), os.getenv("SERVER_A_APICODE"), "🇬🇧", "Server A", "206694", "726322101786509335")
    serverB = FS22ServerConfig(1, os.getenv("SERVER_B_IP"), os.getenv(
        "SERVER_B_PORT"), os.getenv("SERVER_B_APICODE"), "🇵🇱", "Server B", "FFFF00", "726322101786509335")
    serverC = FS22ServerConfig(2, os.getenv("SERVER_C_IP"), os.getenv(
        "SERVER_C_PORT"), os.getenv("SERVER_C_APICODE"), "🇩🇪", "Server C", "57F288", "726322101786509335")
    serverD = FS22ServerConfig(3, os.getenv("SERVER_D_IP"), os.getenv(
        "SERVER_D_PORT"), os.getenv("SERVER_D_APICODE"), "🇮🇹", "Server D", "9C59B6", "726322101786509335")

    serverConfigs = {0: serverA, 1: serverB, 2: serverC, 3: serverD}
    commandHandler.restore_servers(serverConfigs)

    for serverConfig in serverConfigs.values():
        tracker = ServerTracker(serverConfig)
        tracker.events.initial += infoPanelHandler.on_initial_event
        tracker.events.updated += infoPanelHandler.on_updated
        tracker.events.updated += summaryHandler.on_updated
        tracker.events.playerWentOnline += playerStatusHandler.on_player_online
        tracker.events.playerWentOffline += playerStatusHandler.on_player_offline
        tracker.events.playerAdminStateChanged += playerStatusHandler.on_player_admin
        tracker.events.serverStatusChanged += serverStatusHandler.on_server_status_changed
        tracker.events.serverStatusChanged += summaryHandler.on_server_status_changed
        tracker.events.playerCountChanged += summaryHandler.on_player_count_changed
        tracker.start_tracker()

    print("[INFO ] [main] Finished initialization")
    infoPanelHandler.start()
    playerStatusHandler.start()
    serverStatusHandler.start()
    summaryHandler.start()

    global stopped
    while stopped == False:
        await asyncio.sleep(5)
        handlePotentialTaskException(infoPanelHandler.task, "Info Panel Handler")
        handlePotentialTaskException(playerStatusHandler.task, "Player Status Handler")
        handlePotentialTaskException(serverStatusHandler.task, "Server Status Handler")
        handlePotentialTaskException(summaryHandler.task, "Summary Handler")

    print("[INFO ] [main] Waiting for threads to end")
    infoPanelHandler.stop()
    playerStatusHandler.stop()
    serverStatusHandler.stop()
    summaryHandler.stop()

    await infoPanelHandler.wait_for_completion()
    await playerStatusHandler.wait_for_completion()
    await serverStatusHandler.wait_for_completion()
    await summaryHandler.wait_for_completion()
    print("[INFO ] [main] Done")

    await client.close()

def handlePotentialTaskException(task, title):
    if task.done() and not task.cancelled():
        exc = task.exception()
        if exc is not None:
            print(f"[ERROR] [main] {title} encountered an exception: {exc}")
            print(f"[ERROR] [main] Traceback: {task.get_stack()}")

def signal_handler(sig, frame):
    print("[INFO ] [main] Caught Ctrl+C. Stopping")
    global stopped
    if stopped == True:
        print("[INFO ] [main] Second Ctrl+C. Exiting immediately")
        sys.exit(0)
    else:
        stopped = True


signal.signal(signal.SIGINT, signal_handler)
try:
    if os.getenv("SERVER_A_IP") is None:
        print("[INFO ] [main] Loading local environment")
        load_dotenv()
    else:
        print("[INFO ] [main] Using existing environment")

    print("[INFO ] [main] Running client")
    token = os.getenv("DISCORD_TOKEN")
    client.run(token)
    print("[INFO ] [main] Discord client.run() returned")
except Exception:
    print(f"[ERROR] [main] {traceback.format_exc()}")
