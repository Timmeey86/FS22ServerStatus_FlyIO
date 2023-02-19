from fs22server import FS22ServerAccess, FS22ServerConfig, FS22ServerStatus

dummyIp = '51.195.180.13'
dummyPort = '5018'
dummyCode = 'bfaa64a92c3302c1b7ead2212bd08d1a'

dummyConfig = FS22ServerConfig(dummyIp, dummyPort, dummyCode)

dummyServer = FS22ServerAccess(dummyConfig)

currentStatus = dummyServer.get_current_status()
print(currentStatus.__dict__)