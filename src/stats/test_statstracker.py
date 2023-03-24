from statstracker import PlayerServerStats, ServerPlayerStats, DailyStats, HelperFuncs
import unittest
import datetime

class TestPlayerServerStats(unittest.TestCase):
    
    def setUp(self):
        self.sut = PlayerServerStats("Timmeey")
        self.sut.add_online_time(0, 2)
        self.sut.add_online_time(1, 5)
        self.sut.add_online_time(0, 4)

    def test_playerserverstats_onlineTimes(self):
        expectedDict = {0: 6, 1: 5}
        self.assertEqual(self.sut.onlineTimes, expectedDict)

    def test_playerserverstats_serialization(self):
        j = HelperFuncs().to_json(self.sut)
        j2 = HelperFuncs.to_json(PlayerServerStats.from_json(j))
        self.assertEqual(j, j2)

class TestServerPlayerStats(unittest.TestCase):
    
    def setUp(self):
        self.sut = ServerPlayerStats(0)
        self.sut.add_online_time("Timmeey", 5)
        self.sut.add_online_time("Gobbles", 4)
        self.sut.add_online_time("Timmeey", 3)

    def test_serverplayerstats_onlineTimes(self):
        expectedDict = {"Timmeey": 8, "Gobbles": 4}
        self.assertEqual(self.sut.onlineTimes, expectedDict)

    def test_serverplayerstats_serialization(self):
        j = HelperFuncs().to_json(self.sut)
        j2 = HelperFuncs.to_json(ServerPlayerStats.from_json(j))
        self.assertEqual(j, j2)

class TestDailyStats(unittest.TestCase):

    def setUp(self):
        self.sut = DailyStats(datetime.date.today())
        self.sut.add_online_time(0, "Gobbles", 1)
        self.sut.add_online_time(0, "Timmeey", 5)
        self.sut.add_online_time(0, "Gobbles", 2)
        self.sut.add_online_time(1, "Timmeey", 4)
        self.sut.add_online_time(1, "Timmeey", 7)
    
    def test_onlineTimes(self):
        self.assertEqual(self.sut.get_online_time("Timmeey"), 5+4+7)
        self.assertEqual(self.sut.get_online_time("Gobbles"), 1+2)
        self.assertEqual(self.sut.get_online_time("Invalid"), 0)
        
    def test_serverStats(self):
        expectedDict = {"Timmeey": 5, "Gobbles": 3}
        self.assertEqual(self.sut.get_server_stats(0), expectedDict)
        self.assertEqual(self.sut.get_server_stats(500), {})

if __name__ == "__main__":
    unittest.main()