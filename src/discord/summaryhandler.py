from threading import Lock
from fs22.fs22server import OnlineState
import asyncio
import discord
import traceback
import copy
import datetime
import time


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
        self.debug = False

    def add_config(self, serverId, summaryConfig):
        with self.lock:
            self.configs[serverId] = summaryConfig
            if serverId not in self.pendingData:
                self.pendingData[serverId] = None
            # else: Updates were received before the config was added - keep those updates
            self.currentData[serverId] = None

    def get_config(self, serverId):
        with self.lock:
            return None if serverId not in self.configs else self.configs[serverId]

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

    async def wait_for_completion(self):
        counter = 0
        while counter < 70 and not self.task.done():
            await asyncio.sleep(1)
            counter += 1
        self.task = None

    ### Discord update ###

    async def process_updates(self):
        while self.enabled == True:
            # Sleep 60 seconds, but abort at any time when requested
            for _ in range(1, 60):
                await asyncio.sleep(1)
                if self.enabled == False:
                    return
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

                    if not self.update_is_necessary(serverId, pending, current):
                        continue

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

    def update_is_necessary(self, serverId, pending, current):
        self.debugPrint(
            f"Validating if update is necessary for server {serverId}")
        if current is None:
            self.debugPrint(
                "Update is allowed since this is the first one")
            return True
        if current.maxPlayers == pending.maxPlayers and current.onlinePlayers == pending.onlinePlayers and current.onlineState == pending.onlineState:
            self.debugPrint(
                "Deleting update since it would not change anything")
            with self.lock:
                self.pendingData[serverId] = None
            return False
        if (datetime.datetime.now() - current.timestamp).total_seconds() < 360:
            self.debugPrint(
                "Delaying update since the last one was less than six minutes ago")
            return False
        else:
            self.debugPrint("Update is necessary")
            return True

    ### Event listeners ###

    def on_updated(self, serverId, serverData):
        with self.lock:
            self.pendingData[serverId] = SummaryStatus(
                str(len(serverData.onlinePlayers)), serverData.maxPlayers, serverData.status, None)