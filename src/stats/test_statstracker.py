from statstracker import PlayerServerStats, ServerPlayerStats, DailyStats, TotalStats, HelperFuncs
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
        self.sut = DailyStats()
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

class TestTotalStats(unittest.TestCase):

    def setUp(self):
        self.numDays = 3
        self.stats: dict[int, DailyStats] = {i : DailyStats() for i in range(self.numDays)}
        self.stats[0].add_online_time(0, "Timmeey", 5)
        self.stats[0].add_online_time(0, "Gobbles", 3)        
        self.stats[0].add_online_time(1, "Timmeey", 4)
        self.stats[1].add_online_time(0, "Timmeey", 2)
        self.stats[2].add_online_time(0, "Gobbles", 5)
        self.lastUpdate = datetime.date.today() - datetime.timedelta(days=1) # yesterday
        self.sut = TotalStats(self.stats, self.lastUpdate)

    def test_onlineTimes(self):
        self.assertEqual(self.sut.get_online_time("Timmeey"), 5+4+2)
        self.assertEqual(self.sut.get_online_time("Gobbles"), 3+5)

    def test_serverStats(self):
        expectedDict = {
            "Timmeey": 5+4+2,
            "Gobbles": 3+5
        }
        self.assertEqual(self.sut.get_server_stats(0), expectedDict)

    

if __name__ == "__main__":
    unittest.main()