from enum import Enum
import urllib3
import xmltodict


class FS22ServerConfig:
    """Contains data required for accessing an FS22 server"""

    def __init__(self, id, ip, port, apiCode):
        self.id = id
        self.ip = ip
        self.port = port
        self.apiCode = apiCode

    def status_xml_url(self):
        """Retrieves the URL to the XML file which provides status information about the server"""
        return "http://%s:%s/feed/dedicated-server-stats.xml?code=%s" % (self.ip, self.port, self.apiCode)


class OnlineState(Enum):
    Unknown = 0,
    Offline = 1,
    Online = 2

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


class FS22ServerAccess:
    """Handles retrieval of the server status from a FS22 server status XML"""

    def __init__(self, serverConfig):
        self.serverXmlUrl = serverConfig.status_xml_url()

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
                except Exception as e:
                    print("Parsing error: %s\n" % e)
            else:
                print("HTTP Error: %s\n" % response.status)
        except urllib3.exceptions.HTTPError as e:
            print("HTTP Error: %s\n" % e)

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
                statusData.status = OnlineState.Online
                statusData.serverName = serverXmlElement["@name"]
                statusData.mapName = serverXmlElement["@mapName"]
                statusData.maxPlayers = serverXmlElement["Slots"]["@capacity"]
                statusData.dayTime = serverXmlElement["@dayTime"]
                for playerElement in serverXmlElement["Slots"]["Player"]:
                    # Skip empty slots
                    if playerElement is None or playerElement["@isUsed"] == "false":
                        continue
                    
                    playerStatus = FS22PlayerStatus.from_xml(playerElement)
                    statusData.onlinePlayers[playerStatus.playerName] = playerStatus

        return statusData
