import datetime
import json
from json import JSONEncoder, JSONDecoder


class HelperFuncs:
    @staticmethod
    def date_to_json(d: datetime.date) -> str:
        return d.isoformat()

    @staticmethod
    def json_to_date(jsonStr: str) -> datetime.date:
        return datetime.date.fromisoformat(jsonStr)

    @staticmethod
    def to_json(obj) -> str:
        return json.dumps(obj, default=lambda innerObj: getattr(innerObj, '__dict__', str(innerObj)))


class PlayerServerStats:
    """This class stores the online times of a single player on different servers for a single day"""

    def __init__(self, playerName: str):
        self.playerName = playerName
        self.onlineTimes = {}

    def add_online_time(self, serverId: int, onlineTime: int):
        if serverId not in self.onlineTimes:
            self.onlineTimes[serverId] = 0
        self.onlineTimes[serverId] += onlineTime

    @classmethod
    def from_json(cls, jsonStr: str):
        data: dict = json.loads(jsonStr)
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
    def from_json(cls, jsonStr: str):
        data: dict = json.loads(jsonStr)
        serverId = int(data["serverId"])
        onlineTimes = {
            playerName: int(onlineTime) for playerName, onlineTime in data["onlineTimes"].items()
        }
        result = cls(serverId)
        result.onlineTimes = onlineTimes
        return result


class DailyStats:
    """This class stores the online times of various players on various servers for a single day"""

    def __init__(self, theDate: datetime.date):
        self.dateStr = HelperFuncs().date_to_json(theDate)
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
