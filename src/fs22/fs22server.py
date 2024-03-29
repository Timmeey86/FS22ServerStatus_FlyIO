from enum import Enum
import urllib3
import xmltodict
import traceback


class FS22ServerConfig:
    """Contains data required for accessing an FS22 server"""

    def __init__(self, id, ip, port, apiCode, icon, title, color, guildId):
        self.id = id
        self.ip = ip
        self.port = port
        self.apiCode = apiCode
        self.icon = icon
        self.title = title
        self.color = color
        self.guildId = guildId

    def status_xml_url(self):
        """Retrieves the URL to the XML file which provides status information about the server"""
        return f"http://{self.ip}:{self.port}/feed/dedicated-server-stats.xml?code={self.apiCode}"


class OnlineState(str, Enum):
    Unknown = "unknown",
    Offline = "offline",
    Online = "online"


class FS22PlayerStatus:
    """
    Contains information about the current status of a player
    """

    def __init__(self, playerName, onlineTime, isAdmin):
        self.playerName = playerName
        self.onlineTime = onlineTime
        self.isAdmin = isAdmin

    @classmethod
    def from_xml(cls, playerElement):
        return cls(playerElement["#text"], playerElement["@uptime"],
                   playerElement["@isAdmin"])


class FS22ServerStatus:
    """Contains raw data provided by the server XML"""

    def __init__(self):
        self.status = OnlineState.Unknown
        self.serverName = "Unknown"
        self.mapName = "Unknown"
        self.maxPlayers = "Unknown"
        self.onlinePlayers = {}
        self.dayTime = "0"
        self.version = "pending"


class FS22ServerAccess:
    """Handles retrieval of the server status from a FS22 server status XML"""

    def __init__(self, serverConfig):
        self.serverXmlUrl = serverConfig.status_xml_url()
        self.serverConfig = serverConfig

    def get_current_status(self):
        """Retrieves the current server status from the XML file"""

        xmlData = self.get_xml_from_server()
        return self.parse_xml_data(xmlData)

    def get_xml_from_server(self):
        """Tries retrieving the current XML data from the server. XML data are returned as a nested dictionary."""
        http = urllib3.PoolManager()
        try:
            response = http.request(
                "GET", self.serverXmlUrl, timeout=urllib3.util.Timeout(2))
            if response.status == 200:
                try:
                    return xmltodict.parse(response.data)
                except Exception:
                    print(f"[WARN ] [FS22Server] Could not parse data of server {self.serverConfig.id}: {traceback.format_exc()}")
            else:
                print(f"[WARN ] [FS22Server] Reached server {self.serverConfig.id}, but failed reading XML: HTTP Response Code {response.status}")
        except Exception:
            print(f"[INFO ] [FS22Server] Server {self.serverConfig.id} unreachable")

        return None

    def parse_xml_data(self, xmlData):
        """Parses the XML data of the server and transforms it into an FS22ServerStatus object"""

        statusData = FS22ServerStatus()
        if xmlData is None:
            statusData.status = OnlineState.Unknown
        else:
            serverXmlElement = xmlData["Server"]
            if "@name" not in serverXmlElement:
                # If the host is online, but the game server is offline, we get an empty XML
                statusData.status = OnlineState.Offline
            else:
                self.update_status_data(statusData, serverXmlElement)
        return statusData

    def update_status_data(self, statusData, serverXmlElement):
        statusData.status = OnlineState.Online
        statusData.serverName = serverXmlElement["@name"]
        statusData.mapName = serverXmlElement["@mapName"]
        statusData.maxPlayers = serverXmlElement["Slots"]["@capacity"]
        statusData.dayTime = serverXmlElement["@dayTime"]
        statusData.version = serverXmlElement["@version"]
        for playerElement in serverXmlElement["Slots"]["Player"]:
            # Skip empty slots
            if playerElement is None or playerElement["@isUsed"] == "false":
                continue

            playerStatus = FS22PlayerStatus.from_xml(playerElement)
            statusData.onlinePlayers[playerStatus.playerName] = playerStatus
