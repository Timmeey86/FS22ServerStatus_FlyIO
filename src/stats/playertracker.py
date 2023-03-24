from fs22.servertracker import FS22ServerStatus
from stats.statstracker import OnlineTimeTracker

class PlayerTracker:

    def __init__(self, timeTracker: OnlineTimeTracker):
        self.lastKnownPlayerTimes: dict[str, int] = {}
        self.timeTracker = timeTracker

    def on_player_offline(self, serverId: int, playerName: str):
        if playerName in self.lastKnownPlayerTimes:
            onlineTime = self.lastKnownPlayerTimes[playerName]
            self.timeTracker.add_online_time(serverId, playerName, onlineTime)

    def on_updated(self, serverId: int, serverData: FS22ServerStatus):
        for playerData in serverData.onlinePlayers.values():
            self.lastKnownPlayerTimes[playerData.playerName] = int(playerData.onlineTime)

    def get_current_data(self) -> str:
        return self.timeTracker.to_json()