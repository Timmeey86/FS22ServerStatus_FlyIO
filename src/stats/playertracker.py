from fs22.servertracker import FS22ServerStatus
from stats.statstracker import OnlineTimeTracker
from events import Events


class PlayerTrackerEvents(Events):
    """Defines events to be subscribed to"""
    __events__ = ('stats_updated')


class PlayerTracker:

    def __init__(self, timeTracker: OnlineTimeTracker):
        self.lastKnownPlayerTimes: dict[str, int] = {}
        self.timeTracker = timeTracker
        self.events = PlayerTrackerEvents()

    def on_player_offline(self, serverId: int, playerName: str):
        if playerName in self.lastKnownPlayerTimes:
            onlineTime = self.lastKnownPlayerTimes[playerName]
            self.timeTracker.add_online_time(serverId, playerName, onlineTime)
            self.events.stats_updated(self.get_current_data())

    def on_updated(self, serverId: int, serverData: FS22ServerStatus):
        for playerData in serverData.onlinePlayers.values():
            self.lastKnownPlayerTimes[playerData.playerName] = int(playerData.onlineTime)

    def get_current_data(self) -> str:
        return self.timeTracker.to_json()