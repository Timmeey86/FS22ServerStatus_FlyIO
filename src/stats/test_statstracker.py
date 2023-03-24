from statstracker import PlayerServerStats, ServerPlayerStats, DailyStats, TotalStats, HelperFuncs
import unittest
import datetime

MOST_RECENT_DAY = 0
ONE_DAY_BEFORE = 1
TWO_DAYS_BEFORE = 2
FIRST_SERVER = 0
SECOND_SERVER = 1
FIRST_PLAYER = "Player 1"
SECOND_PLAYER = "Player 2"

class TestPlayerServerStats(unittest.TestCase):
    
    def setUp(self):
        self.sut = PlayerServerStats(FIRST_PLAYER)
        self.sut.add_online_time(FIRST_SERVER, 2)
        self.sut.add_online_time(SECOND_SERVER, 5)
        self.sut.add_online_time(FIRST_SERVER, 4)

    def test_playerserverstats_onlineTimes(self):
        expectedDict = {FIRST_SERVER: 6, SECOND_SERVER: 5}
        self.assertEqual(self.sut.onlineTimes, expectedDict)

    def test_playerserverstats_serialization(self):
        j = HelperFuncs().to_json(self.sut)
        j2 = HelperFuncs.to_json(PlayerServerStats.from_json(j))
        self.assertEqual(j, j2)

class TestServerPlayerStats(unittest.TestCase):
    
    def setUp(self):
        self.sut = ServerPlayerStats(FIRST_SERVER)
        self.sut.add_online_time(FIRST_PLAYER, 5)
        self.sut.add_online_time(SECOND_PLAYER, 4)
        self.sut.add_online_time(FIRST_PLAYER, 3)

    def test_serverplayerstats_onlineTimes(self):
        expectedDict = {FIRST_PLAYER: 8, SECOND_PLAYER: 4}
        self.assertEqual(self.sut.onlineTimes, expectedDict)

    def test_serverplayerstats_serialization(self):
        j = HelperFuncs().to_json(self.sut)
        j2 = HelperFuncs.to_json(ServerPlayerStats.from_json(j))
        self.assertEqual(j, j2)

class TestDailyStats(unittest.TestCase):

    def setUp(self):
        self.sut = DailyStats()
        self.sut.add_online_time(FIRST_SERVER, SECOND_PLAYER, 1)
        self.sut.add_online_time(FIRST_SERVER, FIRST_PLAYER, 5)
        self.sut.add_online_time(FIRST_SERVER, SECOND_PLAYER, 2)
        self.sut.add_online_time(SECOND_SERVER, FIRST_PLAYER, 4)
        self.sut.add_online_time(SECOND_SERVER, FIRST_PLAYER, 7)
    
    def test_onlineTimes(self):
        self.assertEqual(self.sut.get_online_time(FIRST_PLAYER), 5+4+7)
        self.assertEqual(self.sut.get_online_time(SECOND_PLAYER), 1+2)
        self.assertEqual(self.sut.get_online_time("Invalid"), 0)

    def test_serverStats(self):
        expectedDict = {FIRST_PLAYER: 5, SECOND_PLAYER: 3}
        self.assertEqual(self.sut.get_server_stats(FIRST_SERVER), expectedDict)
        self.assertEqual(self.sut.get_server_stats(500), {})

class TestTotalStats(unittest.TestCase):

    def setUp(self):
        self.numDays = 3
        self.stats: dict[int, DailyStats] = {i : DailyStats() for i in range(self.numDays)}
        self.stats[MOST_RECENT_DAY].add_online_time(FIRST_SERVER, FIRST_PLAYER, 5)
        self.stats[MOST_RECENT_DAY].add_online_time(FIRST_SERVER, SECOND_PLAYER, 3)        
        self.stats[MOST_RECENT_DAY].add_online_time(SECOND_SERVER, FIRST_PLAYER, 4)
        self.stats[ONE_DAY_BEFORE].add_online_time(FIRST_SERVER, FIRST_PLAYER, 2)
        self.stats[TWO_DAYS_BEFORE].add_online_time(FIRST_SERVER, SECOND_PLAYER, 5)
        self.lastUpdate = datetime.date.today() - datetime.timedelta(days=1) # yesterday
        self.sut = TotalStats(self.stats, self.lastUpdate)

    def test_onlineTimes(self):
        self.assertEqual(self.sut.get_online_time(FIRST_PLAYER), 5+4+2)
        self.assertEqual(self.sut.get_online_time(SECOND_PLAYER), 3+5)

    def test_totalStats(self):
        expectedDict = {
            FIRST_PLAYER: 5+4+2,
            SECOND_PLAYER: 3+5
        }
        self.assertEqual(self.sut.get_total_stats(), expectedDict)

    def test_serverStats(self):
        expectedDictServer0 = {
            FIRST_PLAYER: 5+2,
            SECOND_PLAYER: 3+5
        }
        expectedDictServer1 = {
            FIRST_PLAYER: 4
        }
        self.assertEqual(self.sut.get_server_stats(0), expectedDictServer0)
        self.assertEqual(self.sut.get_server_stats(1), expectedDictServer1)

    def test_dayShift(self):

        lengthBefore = len(self.sut.stats)
        onlineTimeBefore_P1 = self.sut.get_online_time(FIRST_PLAYER)
        onlineTimeBefore_P2 = self.sut.get_online_time(SECOND_PLAYER)

        self.sut.add_online_time(FIRST_SERVER, FIRST_PLAYER, 10)

        self.assertEqual(len(self.sut.stats), lengthBefore, "The amount of entries should be unchanged")
        self.assertEqual(self.sut.get_online_time(FIRST_PLAYER), onlineTimeBefore_P1 + 10, f"The online time of {FIRST_PLAYER} should be increased by 10")
        self.assertEqual(self.sut.get_online_time(SECOND_PLAYER), onlineTimeBefore_P2 - 5, f"The oldest entry of {SECOND_PLAYER} should have timed out")
    
    def test_multiDayShift(self):

        self.sut.lastUpdate = datetime.date.today() - datetime.timedelta(days=self.numDays)
        self.sut.add_online_time(0, "DUMMY", 0)

        self.assertEqual(self.sut.get_online_time(FIRST_PLAYER), 0)
        self.assertEqual(self.sut.get_online_time(SECOND_PLAYER), 0)

    def test_emptyStatsTracker(self):
        sut2 = TotalStats.create_new()
        sut2.add_online_time(FIRST_SERVER, FIRST_PLAYER, 1)

        self.assertEqual(sut2.get_online_time(FIRST_PLAYER), 1)

if __name__ == "__main__":
    unittest.main()
