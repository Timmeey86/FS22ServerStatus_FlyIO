import datetime
import json
from json import JSONEncoder, JSONDecoder


class HelperFuncs:
    @staticmethod
    def date_to_json(d: datetime.date) -> str:
        return d.isoformat() if d else "null"

    @staticmethod
    def json_to_date(jsonStr: str) -> datetime.date:
        return None if jsonStr == "null" else datetime.date.fromisoformat(jsonStr)

    @staticmethod
    def to_json(obj, indentation=None) -> str:
        return json.dumps(obj, indent=indentation, default=lambda innerObj: getattr(innerObj, '__dict__', str(innerObj)))


class PlayerServerStats:
    """This class stores the online times of a single player on different servers for a single day"""

    def __init__(self, playerName: str):
        self.playerName: str = playerName
        self.onlineTimes: dict[int, int] = {}

    def add_online_time(self, serverId: int, onlineTime: int):
        if serverId not in self.onlineTimes:
            self.onlineTimes[serverId] = 0
        self.onlineTimes[serverId] += onlineTime

    @classmethod
    def from_dict(cls, data: dict[str, any]):
        playerName: str = data["playerName"]
        onlineTimes = {
            int(serverId): int(onlineTime) for serverId, onlineTime in data["onlineTimes"].items()
        }
        result = cls(playerName)
        result.onlineTimes = onlineTimes
        return result


class ServerPlayerStats:
    """This class stores the online times of different players on a single server for a single day"""

    def __init__(self, serverId: int):
        self.serverId = serverId
        self.onlineTimes = {}

    def add_online_time(self, playerName: str, onlineTime: int):
        if playerName not in self.onlineTimes:
            self.onlineTimes[playerName] = 0
        self.onlineTimes[playerName] += onlineTime

    @classmethod
    def from_dict(cls, data: dict[str, any]):
        serverId = int(data["serverId"])
        onlineTimes = {
            playerName: int(onlineTime) for playerName, onlineTime in data["onlineTimes"].items()
        }
        result = cls(serverId)
        result.onlineTimes = onlineTimes
        return result


class DailyStats:
    """This class stores the online times of various players on various servers for a single day"""

    def __init__(self):
        self.statsPerPlayer: dict[str, PlayerServerStats] = {}
        self.statsPerServer: dict[int, ServerPlayerStats] = {}

    def add_online_time(self, serverId: int, playerName: str, onlineTime: int):
        if serverId not in self.statsPerServer:
            self.statsPerServer[serverId] = ServerPlayerStats(serverId)
        self.statsPerServer[serverId].add_online_time(playerName, onlineTime)

        if playerName not in self.statsPerPlayer:
            self.statsPerPlayer[playerName] = PlayerServerStats(playerName)
        self.statsPerPlayer[playerName].add_online_time(serverId, onlineTime)

    def get_online_time(self, playerName: str) -> int:
        if playerName in self.statsPerPlayer:
            return sum(self.statsPerPlayer[playerName].onlineTimes.values())
        return 0

    def get_server_stats(self, serverId: int) -> dict[str, int]:
        if serverId in self.statsPerServer:
            return self.statsPerServer[serverId].onlineTimes
        return {}

    def get_online_players(self) -> list[str]:
        return self.statsPerPlayer.keys()

    def get_servers(self) -> list[int]:
        return self.statsPerServer.keys()

    @classmethod
    def from_dict(cls, data: dict[str, dict[str, any]]):
        result = cls()
        result.statsPerPlayer = {
            playerName: PlayerServerStats.from_dict(dailyData)
            for playerName, dailyData in data["statsPerPlayer"].items()}
        result.statsPerServer = {
            int(serverIdStr): ServerPlayerStats.from_dict(dailyData)
            for serverIdStr, dailyData in data["statsPerServer"].items()}
        return result


class TotalStats:
    """This class keeps track of the online times of configured amount of days"""

    def __init__(self, stats: dict[int, DailyStats], lastUpdate: datetime.date):
        self.stats = stats
        self.lastUpdate = lastUpdate

    @classmethod
    def create_new(cls, maxDays: int = 14):
        stats: dict[int, DailyStats] = {
            i: DailyStats() for i in range(maxDays - 1)}
        return cls(stats=stats, lastUpdate=None)

    def get_online_time(self, playerName: str) -> int:
        return sum(stats.get_online_time(playerName) for stats in self.stats.values())

    def get_total_stats(self) -> dict[str, int]:
        """Counts the total online times for each player, independent of day and server"""
        stats: dict[str, int] = {}
        for dailyStats in self.stats.values():
            for playerName in dailyStats.get_online_players():
                if playerName not in stats:
                    stats[playerName] = 0
                stats[playerName] += dailyStats.get_online_time(playerName)
        return stats

    def get_server_stats(self, serverId: int) -> dict[str, int]:
        """Counts the total online times for each player, independent of the day, but for a single server only"""
        stats: dict[str, int] = {}
        for dailyStats in self.stats.values():
            for playerName, onlineTime in dailyStats.get_server_stats(serverId).items():
                if playerName not in stats:
                    stats[playerName] = 0
                stats[playerName] += onlineTime
        return stats

    def add_online_time(self, serverId: int, playerName: str, onlineTime: int):
        """Adds an online time for the given player for today"""
        today = datetime.date.today()
        if not self.lastUpdate:
            self.lastUpdate = today
        daysSinceLastUdpate = (today - self.lastUpdate).days
        if daysSinceLastUdpate > 0:
            self.shift_entries(daysSinceLastUdpate)
            self.lastUpdate = today
        self.stats[0].add_online_time(serverId, playerName, onlineTime)

    def shift_entries(self, daysSinceLastUdpate: int):
        """Shifts all entries by one, dropping the last one and adding an empty first one.

        If nobody has been online on a given day, or the bot was offline, data will be shifted accordingly."""
        numEntries = len(self.stats)
        for _ in range(daysSinceLastUdpate):
            for i in range(numEntries - 1, 0, -1):
                self.stats[i] = self.stats[i-1]
            self.stats[0] = DailyStats()

    def to_json(self, indent=None) -> str:
        tmpDict = {"lastUpdate": HelperFuncs().date_to_json(self.lastUpdate)}
        tmpDict["stats"] = self.stats
        return HelperFuncs().to_json(tmpDict, indent)

    @classmethod
    def from_json(cls, j: str):
        tmpDict = json.loads(j)

        lastUpdate: datetime.date = HelperFuncs(
        ).json_to_date(tmpDict["lastUpdate"])
        tmpStats: dict[str, dict[str, dict[str, any]]] = tmpDict["stats"]
        stats: dict[int, DailyStats] = {
            int(indexStr): DailyStats.from_dict(dailyStatsDict)
            for indexStr, dailyStatsDict in tmpStats.items()
        }
        return cls(stats, lastUpdate)
