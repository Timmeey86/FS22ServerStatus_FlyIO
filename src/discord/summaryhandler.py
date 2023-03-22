from threading import Lock
from fs22.fs22server import OnlineState
import asyncio
import discord
import traceback
import copy
import datetime


class SummaryConfig:
    """This class stores the fixed information about a summary reporting channel"""

    def __init__(self, shortName, channel):
        self.shortName = shortName
        self.channel = channel


class SummaryStatus:
    """Represents the current - or a future - state of a summary channel"""

    def __init__(self, onlinePlayers, maxPlayers, onlineState, timestamp):
        self.onlinePlayers = onlinePlayers
        self.maxPlayers = maxPlayers
        self.onlineState = onlineState
        self.timestamp = timestamp


class SummaryHandler:
    """This class is responsible for renaming a channel whenever:
    - A server goes offline
    - A server goes online
    - A player joined
    - A player left
    - The maximum amount of possible players changed (rare, but possible, e.g. in case of a server upgrade)

    Since renaming a channel is rate limited to 2 times per 10 minutes per channel,
    this class needs to make sure we don't try more often than that.
    The current implementation simply waits 6 minutes before the next renaming attempt.
    Additionally, it skips an update if e.g. one player joined and another left since
    the last update, or if the server rebooted within the given time.
    """

    def debugPrint(self, message):
        if self.debug == True:
            print(f"[DEBUG] [SummaryHandler] {message}")

    def __init__(self, discordClient):
        self.configs = {}  # Stores a configuration object for every tracked server
        self.pendingData = {}  # Stores a SummaryStatus update to be processed as soon as allowed
        self.currentData = {}  # Stores the current SummaryStatus state
        self.lock = Lock()
        self.enabled = True
        self.task = None
        self.discordClient = discordClient
        self.debug = True

    def add_config(self, serverId, summaryConfig):
        with self.lock:
            self.configs[serverId] = summaryConfig
            if serverId not in self.pendingData:
                self.pendingData[serverId] = None
            # else: Updates were received before the config was added - keep those updates
            self.currentData[serverId] = None

    async def track_server(self, serverId, interaction, shortName):
        summaryConfig = SummaryConfig(shortName, interaction.channel)
        self.add_config(serverId, summaryConfig)

    ### Threading ###

    def start(self):
        if self.task is None:
            self.enabled = True
            self.task = asyncio.create_task(self.process_updates())

    def stop(self):
        if self.task is not None:
            self.enabled = False

    ### Discord update ###

    async def process_updates(self):
        while self.enabled == True:
            # Check every five seconds
            await asyncio.sleep(5)
            self.debugPrint("Waking up")
            # Copy configs and pending data (keep the lock short)
            with self.lock:
                configsCopy = {
                    serverId: self.configs[serverId] for serverId in self.configs}
                pendingDataCopy = {
                    serverId: self.pendingData[serverId] for serverId in self.pendingData}
                currentDataCopy = {
                    serverId: self.currentData[serverId] for serverId in self.currentData}
            self.debugPrint("Copied data")

            # Process copied data now
            for serverId, configCopy in configsCopy.items():
                pending = pendingDataCopy[serverId]
                if pending is not None:
                    current = currentDataCopy[serverId]
                    self.debugPrint(
                        f"Checking timestamp for server ID {serverId}")
                    if current == None:
                        self.debugPrint(
                            "Update is allowed since this is the first one")
                    elif (datetime.datetime.now() - currentDataCopy[serverId].timestamp).total_seconds() < 360:
                        self.debugPrint(
                            "Delaying update since the last one was less than six minutes ago")
                        continue
                    elif current.maxPlayers == pending.maxPlayers and current.onlinePlayers == pending.onlinePlayers and current.onlineState == pending.onlineState:
                        self.debugPrint(
                            "Deleting update since it would not change anything")
                        with self.lock:
                            self.pendingData[serverId] = None
                        continue
                    else:
                        self.debugPrint("Applying update")

                    onlineSign = "🟢" if pending.onlineState == OnlineState.Online else "🔴"
                    try:
                        channelName = f"{onlineSign} {configCopy.shortName}: {pending.onlinePlayers}/{pending.maxPlayers}"
                        self.debugPrint(f"Renaming channel to >>{channelName}<<")
                        await configCopy.channel.edit(name=channelName)
                    except Exception:
                        print(f"[WARN ] [SummaryHandler] Failed renaming the channel: {traceback.format_exc()}")

                    self.debugPrint(
                        "Updating current data and resetting pending data")
                    with self.lock:
                        self.currentData[serverId] = SummaryStatus(
                            pending.onlinePlayers, pending.maxPlayers, pending.onlineState, datetime.datetime.now())
                        self.pendingData[serverId] = None

        print("[INFO ] [SummaryHandler] SummaryHandler was aborted")
        self.task = None

    ### Event listeners ###

    def on_updated(self, serverId, serverData):
        if serverId not in self.configs:
            # The server is not (yet) tracked. Store the update in case it gets tracked later
            with self.lock:
                self.pendingData[serverId] = SummaryStatus(
                    str(len(serverData.onlinePlayers)), serverData.maxPlayers, serverData.status, None)

    def on_server_status_changed(self, serverId, serverData):
        if serverId not in self.configs:
            return
        with self.lock:
            self.debugPrint(f"Server status on tracked server {serverId} changed to {serverData.status}")
            current = self.currentData[serverId]
            if current is not None:
                self.pendingData[serverId] = SummaryStatus(
                    str(len(serverData.onlinePlayers)), serverData.maxPlayers, serverData.status, None)
            else:
                self.pendingData[serverId] = SummaryStatus(
                    "0", serverData.maxPlayers, serverData.status, None)

    def on_player_count_changed(self, serverId, playerCount):
        if serverId not in self.configs:
            return
        with self.lock:
            self.debugPrint(f"Player count on tracked server {serverId} changed to {playerCount}")
            current = self.currentData[serverId]
            if current is not None:
                self.pendingData[serverId] = SummaryStatus(
                    str(playerCount), current.maxPlayers, current.onlineState, None)
            else:
                self.pendingData[serverId] = SummaryStatus(
                    str(playerCount), "0", OnlineState.Unknown, None)