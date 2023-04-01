import discord
import asyncio
import datetime
import traceback
from threading import Lock
from stats.statstracker import OnlineTimeTracker

class StatsReporter:
    """This class is responsible for displaying the online times of players during the last couple of days"""

    def __init__(self, discordClient: discord.Client):
        self.discordClient = discordClient
        self.timeTracker: OnlineTimeTracker = None
        self.task: asyncio.Task = None
        self.enabled: bool = False
        self.embeds: list [discord.Message] = []
        self.guildToServerMap: dict [int, list[int]] = {}
        self.lock: Lock = Lock()
        self.debug = False
        
    def debugPrint(self, message):
        if self.debug == True:
            print(f"[DEBUG] [StatsReporter] {message}")

    def set_time_tracker(self, timeTracker: OnlineTimeTracker):
        with self.lock:
            self.timeTracker = timeTracker

    def update_guild_to_server_map(self, guildToServerMap: dict [int, list[int]]):
        with self.lock:
            self.guildToServerMap = guildToServerMap

    async def add_embed(self, interaction):
        embed = discord.Embed(title="Pending...", color=int("FFFFFF", 16))
        with self.lock:
            self.embeds.append(await interaction.channel.send(embed=embed))

    def restore_embeds(self, embeds):
        with self.lock:
            self.embeds = embeds
        
    ### Threading ###

    def start(self):
        if self.task is None:
            self.enabled = True
            self.task = asyncio.create_task(self.update_panel())

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

    async def update_panel(self):
        self.debugPrint("Processing has started")
        while self.enabled == True:
            # Sleep 60 seconds, but abort at any time when requested
            for _ in range(1, 60):
                await asyncio.sleep(1)
                if self.enabled == False:
                    self.debugPrint("Aborting StatsReporter")
                    return

            self.debugPrint("Waking up")
            with self.lock:
                if not self.timeTracker:
                    self.debugPrint("No time tracker - skipping")
                    continue
                embedListCopy = list(self.embeds)
                guildToServerMapCopy = dict(self.guildToServerMap)

            self.debugPrint("Starting to update embeds")
            for embedMessage in embedListCopy:
                guildId = int(embedMessage.guild.id)
                if guildId not in guildToServerMapCopy:
                    self.debugPrint("No server found for embed - skipping")
                    self.debugPrint(guildToServerMapCopy)
                    self.debugPrint(guildId)
                    continue
                serverIds = guildToServerMapCopy[guildId]
                try:
                    data = self.timeTracker.get_total_stats(serverIds)
                except Exception:
                    print(f"[WARN ] [StatsReporter] Failed retrieving total stats for guild id {guildId}: {traceback.format_exc()}",
                        flush=True)
                    continue
                
                message = "Online times within the last 14 days:\r\n"
                sortedOnlineTimes = dict(sorted(data.items(), key=lambda item: item[1], reverse=True))
                for player, onlineTime in sortedOnlineTimes.items():
                    message += f"\r\n    **{player}**: {onlineTime} minutes"

                # Update the embed
                try:
                    self.debugPrint("Updating embed")
                    newEmbed = discord.Embed(
                        title=f"Online times",
                        description=message,
                        color=embedMessage.embeds[0].color
                    )
                    self.debugPrint("Adding last update field")
                    newEmbed.add_field(name="Last Update", value=f"{datetime.datetime.now()}")
                    self.debugPrint("Updating embed")
                    await embedMessage.edit(embed=newEmbed)
                except Exception:
                    print(
                        f"[WARN ] [StatsReporter] Could not update embed for guild {guildId}: {traceback.format_exc()}",
                        flush=True
                    )

                # don't spam discord
                await asyncio.sleep(3)

        print("[INFO ] [StatsReporter] StatsReporter was aborted", flush=True)

        