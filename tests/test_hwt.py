import os
import unittest
import tempfile
from hwt import hwt


class HwtTestCase(unittest.TestCase):
    def setUp(self):
        self.db_fd, hwt.app.config["DATABASE"] = tempfile.mkstemp()
        hwt.app.config["TESTING"] = True
        self.app = hwt.app.test_client()
        with hwt.app.app_context():
            hwt.init_db()

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(hwt.app.config["DATABASE"])

    def add_deck(self, deck_name, class_name):
        return self.app.post("/add_deck", data=dict(
            deck_name=deck_name,
            class_name=class_name
        ), follow_redirects=True)

    def add_deck_data(self, deck_name, enemy_name, win):
        return self.app.post("/add_game", data=dict(
            deck_name=deck_name,
            enemy_name=enemy_name,
            win=win
        ), follow_redirects=True)

    def get_decks(self):
        return self.app.get("/")

    def test_add_deck(self):
        rv = self.add_deck("test deck", "Druid")
        assert b"Deck was successfully added." in rv.data

    def test_unique_deck_names(self):
        rv = self.add_deck("test deck", "Druid")
        rv = self.add_deck("test deck", "Druid")
        assert b"A deck with that name already exists." in rv.data

    def test_get_decks(self):
        self.add_deck("test deck", "Druid")
        rv = self.get_decks()
        assert b"test deck" in rv.data

    def test_create_deck_table(self):
        self.add_deck("test deck", "Druid")
        self.add_deck("bad test deck", "Rogue")
        rv = self.add_deck_data("test deck", "bad test deck", True)
        assert b"test deck", b"bad test deck" in rv.data

if __name__ == "__main__":
    unittest.main()
