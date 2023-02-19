import asyncio
from fs22server import FS22ServerAccess, FS22ServerConfig, FS22ServerStatus
from servertracker import ServerTracker, ServerTrackerEvents
from dotenv import load_dotenv
import os


async def main():

    load_dotenv()

    serverA = FS22ServerConfig(0, os.getenv("SERVER_A_IP"), os.getenv(
        "SERVER_A_PORT"), os.getenv("SERVER_A_APICODE"))
    serverB = FS22ServerConfig(1, os.getenv("SERVER_B_IP"), os.getenv(
        "SERVER_B_PORT"), os.getenv("SERVER_B_APICODE"))
    serverC = FS22ServerConfig(2, os.getenv("SERVER_C_IP"), os.getenv(
        "SERVER_C_PORT"), os.getenv("SERVER_C_APICODE"))
    serverD = FS22ServerConfig(3, os.getenv("SERVER_D_IP"), os.getenv(
        "SERVER_D_PORT"), os.getenv("SERVER_D_APICODE"))

    serverConfigs = [serverA, serverB, serverC, serverD]

    tracker = ServerTracker(serverC)
    tracker.start_tracker()

    print("Finished initialization")

    while(True):
        await asyncio.sleep(5)

print("Done")

asyncio.run(main())
