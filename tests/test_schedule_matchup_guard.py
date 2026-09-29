"""Unknown opponents are held until the match identity is reviewable."""

import unittest
from pathlib import Path
from sys import path as sys_path


sys_path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from schedule_matchup_guard import unresolved_matchup  # noqa: E402


class ScheduleMatchupGuardTests(unittest.TestCase):
    def test_unresolved_playoff_and_esports_slots_are_held(self):
        for name in ("TBD at TBD", "TBD vs. TBD", "Team A vs. TBA",
                     "To Be Determined at Team B"):
            with self.subTest(name=name):
                self.assertTrue(unresolved_matchup({"name": name}))

    def test_named_fixtures_and_tournament_titles_remain(self):
        for name in ("New York Liberty at Las Vegas Aces", "TBD Championship Tournament",
                     "Team TBD United vs. Team B", "China Open"):
            with self.subTest(name=name):
                self.assertFalse(unresolved_matchup({"name": name}))


if __name__ == "__main__":
    unittest.main()
