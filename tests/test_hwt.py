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
            player_deck=deck_name,
            enemy_deck=enemy_name,
            win=win
        ), follow_redirects=True)

    def remove_deck(self, deck_name):
        return self.app.post("/remove_deck", data=dict(
            deck_name=deck_name
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

    def test_dont_show_decks_with_no_games(self):
        self.add_deck("test deck", "Druid")
        rv = self.get_decks()

        assert b"<h4>test deck</h4>" not in rv.data

    def test_show_decks_with_games(self):
        self.add_deck("test deck", "Druid")
        self.add_deck("bad test deck", "Rogue")
        rv = self.add_deck_data("test deck", "bad test deck", "win")

        assert b"<h4>test deck</h4>" in rv.data
        assert b"<h4>bad test deck</h4>" not in rv.data

    def test_create_deck_table(self):
        self.add_deck("test deck", "Druid")
        self.add_deck("bad test deck", "Rogue")
        rv = self.add_deck_data("test deck", "bad test deck", "win")

        assert b"Game was successfully added." in rv.data

    def test_correct_ratio_formatting(self):
        self.add_deck("test deck", "Druid")
        self.add_deck("bad test deck", "Rogue")
        self.add_deck("other bad test deck", "Mage")
        for k in range(2):
            self.add_deck_data("test deck", "bad test deck", "win")
        self.add_deck_data("test deck", "other bad test deck", "win")
        rv = self.add_deck_data("test deck", "bad test deck", "loss")

        assert b'<h4>75.0 %</h4>'
        assert b'<div class="small-2 columns">66.67 %</div>'
        assert b'<div class="small-2 columns">0 %</div>'

    def test_remove_deck(self):
        self.add_deck("test deck", "Druid")
        self.add_deck("bad test deck", "Rogue")
        self.add_deck_data("test deck", "bad test deck", "win")
        rv = self.remove_deck("bad test deck")

        with hwt.app.app_context():
            db = hwt.get_db()
            query = "SELECT name " \
                    "FROM sqlite_master " \
                    "WHERE type='table';"
            cur = db.execute(query)
            temp = cur.fetchall()
            table_names = []
            for row in temp:
                table_names.append(row["name"])

        assert "d_bad_test_deck" not in table_names
        assert b"<h4>0 %</h4>" in rv.data


if __name__ == "__main__":
    unittest.main()
