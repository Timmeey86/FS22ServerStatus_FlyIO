import asyncio
from discord.infopanelhandler import InfoPanelHandler
from discord.playerstatushandler import PlayerStatusHandler
from discord.serverstatushandler import ServerStatusHandler
from discord.summaryhandler import SummaryHandler
from discord.commandhandler import CommandHandler
from stats.statsreporter import StatsReporter
from persistence import PersistenceDataMapper
from dotenv import load_dotenv
import discord
from discord import app_commands
import os
import signal
import sys
import traceback

stopped = False
firstCallOfOnReady = True

# Create a discord client to allow interacting with a discord server
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# Get the path to the persistent storage (OS dependent)
if os.path.exists("/data"):
    print("[INFO ] [main] Unix detected. Using /data as root directory")
    storageRootPath = "/data"
if os.path.exists("C:/temp"):
    print("[INFO ] [main] Windows detected. Using C:\\temp as root directory")
    storageRootPath = "C:\\temp"

# build the main object tree
infoPanelHandler = InfoPanelHandler(client)
playerStatusHandler = PlayerStatusHandler(client)
serverStatusHandler = ServerStatusHandler(client)
summaryHandler = SummaryHandler(client)
statsReporter = StatsReporter(client)
commandHandler = CommandHandler(infoPanelHandler, playerStatusHandler, serverStatusHandler, summaryHandler, statsReporter)
persistenceDataMapper = PersistenceDataMapper(commandHandler, storageRootPath)

@tree.command(name="fssb_add_embed",
              description="Adds an embed to this channel displaying live info about the FS22 server")
@app_commands.describe(
    id="The ID of the server")
async def fssb_add_embed(interaction, id: int):
    print(f"Received fssb_add_embed command for id {id}")
    await commandHandler.add_embed(interaction, id)
    persistenceDataMapper.store_data()


@tree.command(name="fssb_set_member_status_channel",
              description="Sets this channel as the target channel for online/offline/admin player messages")
@app_commands.describe(
    id="The ID of the server")
async def fssb_set_member_channel(interaction, id: int):
    await commandHandler.set_member_channel(interaction, id)
    persistenceDataMapper.store_data()


@tree.command(name="fssb_set_server_status_channel",
              description="Sets this channel as the target channel for online/offline server messages")
@app_commands.describe(id="The ID of the server")
async def fssb_set_server_channel(interaction, id: int):
    await commandHandler.set_server_channel(interaction, id)
    persistenceDataMapper.store_data()


@tree.command(name="fssb_set_summary_channel",
              description="Make this channel display the online state and player count in its name")
@app_commands.describe(id="The ID of the server", shortname="The short name for the server")
async def fssb_set_summary_channel(interaction, id: int, shortname: str):
    await commandHandler.set_summary_channel(interaction, id, shortname)
    persistenceDataMapper.store_data()


@tree.command(name="fssb_update_summary_channel",
              description="Updates the short name displayed in the channel which shows the member count")
@app_commands.describe(id="The ID of the server", shortname="The new short name for the server")
async def fssb_update_summary_channel(interaction, id: int, shortname: str):
    await commandHandler.update_short_name(interaction, id, shortname)
    persistenceDataMapper.store_data()


@tree.command(name="fssb_set_bot_status_channel",
              description="Make this channel display status messages concerning the bot")
@app_commands.describe()
async def fssb_set_bot_status_channel(interaction):
    await commandHandler.set_bot_status_channel(interaction)
    persistenceDataMapper.store_data()

@tree.command(name="fssb_set_stats_channel",
              description="Creates an embed in this channel which displays online time stats for players")
@app_commands.describe()
async def fssb_set_stats_channel(interaction):
    await commandHandler.set_stats_channel(interaction)
    persistenceDataMapper.store_data()


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
    persistenceDataMapper.store_data()

@tree.command(name="fssb_remove_server",
              description="Stops tracking an FS22 server")
@app_commands.describe(id="The server ID")
async def fssb_remove_server(interaction, id: int):
    await commandHandler.remove_server(interaction, id)
    persistenceDataMapper.store_data()

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

@tree.command(name="fssb_get_tracking_data", description="Retrieves the tracking data")
@app_commands.describe()
async def fssb_get_tracking_data(interaction):
    if not interaction.permissions.administrator:
        await interaction.response.send_message(
            content="Only administrators are allowed to run commands on this bot",
            ephemeral=True,
            delete_after=10)
        return
    trackingData = await persistenceDataMapper.get_tracking_data()
    if trackingData:
        await interaction.response.send_message(
            content=trackingData,
            ephemeral=True)
    else:
        await interaction.response.send_message(
            content="No data",
            ephemeral=True,
            delete_after=1)


@client.event
async def on_ready():
    """
    Tells us when the bot is logged in to discord (in the replit console)
    """
    
    global firstCallOfOnReady
    if firstCallOfOnReady == False:
        return
    firstCallOfOnReady = False

    # Restore existing config first

    await persistenceDataMapper.restore_data(client)

    # Enable slash commands like /fss_add_embed
    print("[INFO ] [main] Discord client is ready")
    print("[INFO ] [main] Waiting for tree sync")
    try:
        await tree.sync()
        print("[INFO ] [main] Tree is now synched")
    except Exception:
        print(f"[INFO ] [main] Failed waiting for tree sync: {traceback.format_exc()}")

    infoPanelHandler.start()
    playerStatusHandler.start()
    serverStatusHandler.start()
    summaryHandler.start()
    statsReporter.start()
    print("[INFO ] [main] Finished initialization")

    global stopped
    while stopped == False:
        await asyncio.sleep(5)
        handlePotentialTaskException(infoPanelHandler.task, "Info Panel Handler")
        handlePotentialTaskException(playerStatusHandler.task, "Player Status Handler")
        handlePotentialTaskException(serverStatusHandler.task, "Server Status Handler")
        handlePotentialTaskException(summaryHandler.task, "Summary Handler")
        handlePotentialTaskException(statsReporter.task, "Stats Reporter")
        sys.stdout.flush()

    print("[INFO ] [main] Waiting for threads to end")
    infoPanelHandler.stop()
    playerStatusHandler.stop()
    serverStatusHandler.stop()
    summaryHandler.stop()
    statsReporter.stop()

    await infoPanelHandler.wait_for_completion()
    await playerStatusHandler.wait_for_completion()
    await serverStatusHandler.wait_for_completion()
    await summaryHandler.wait_for_completion()
    await statsReporter.wait_for_completion()
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
    if os.getenv("DISCORD_TOKEN") is None:
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
