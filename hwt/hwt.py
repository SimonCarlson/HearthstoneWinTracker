import os
import sqlite3
from flask import Flask, render_template, g, request, flash, redirect, url_for

app = Flask(__name__)
app.config.from_object(__name__)

app.config.update(dict(
    DATABASE=os.path.join(app.root_path, "hwt.db"),
    SECRET_KEY="development key",
))
app.config.from_envvar("HWT_SETTINGS", silent=True)


@app.route("/")
def show_entries():
    decks = get_all_deck_info()
    return render_template("show_entries.html", deck_info=decks)


@app.route("/add_deck", methods=["GET", "POST"])
def add_deck():
    classes = ["Druid", "Hunter", "Mage", "Paladin", "Priest", "Rogue", "Shaman", "Warlock", "Warrior"]

    if request.method == "POST":
        db = get_db()
        query = "INSERT INTO decks (name, class) VALUES (?, ?)"
        try:
            db.execute(query, [request.form["deck_name"], request.form["class_name"]])
            db.commit()
            table_name = "d_" + request.form["deck_name"].replace(" ", "_")
            query = "CREATE TABLE {} (" \
                    "id INTEGER PRIMARY KEY AUTOINCREMENT," \
                    "player INTEGER REFERENCES decks(id)," \
                    "enemy INTEGER REFERENCES decks(id)," \
                    "wins INTEGER," \
                    "losses INTEGER" \
                    ")".format(table_name)
            db.execute(query)
            db.commit()
            flash("Deck was successfully added.")
            return redirect(url_for("show_entries"))
        except sqlite3.IntegrityError as e:
            # print("Integrity error.")
            flash("A deck with that name already exists.")
        except sqlite3.Error:
            flash("Something went wrong, try again.")

    return render_template("add_deck.html", classes=classes)


@app.route("/add_game", methods=["GET", "POST"])
def add_game():
    db = get_db()
    query = "SELECT name FROM decks;"
    cur = db.execute(query)
    decks = cur.fetchall()

    if request.method == "POST":
        player_deck = request.form["player_deck"]
        enemy_deck = request.form["enemy_deck"]
        print("PLAYER DECK: " + player_deck)
        print("ENEMY DECK: " + enemy_deck)
        win = request.form["win"]
        table_name = "d_" + request.form["player_deck"].replace(" ", "_")

        query = "SELECT id FROM {} " \
                "WHERE player = " \
                "(SELECT id FROM decks WHERE name = '{}') " \
                "AND enemy = " \
                "(SELECT id FROM decks WHERE name = '{}');".format(table_name, player_deck, enemy_deck)
        cur = db.execute(query)
        row_id = cur.fetchone()

        if row_id is not None:
            print("UPDATING EXISTING ROW. ID: " + str(row_id[0]))
            # there is a row for that player deck and enemy deck, update it
            if win == "win":
                print("IT WAS A WIN.")
                query = "UPDATE {} " \
                        "SET wins = " \
                        "(SELECT wins FROM {} WHERE id = {}) + 1 " \
                        "WHERE id = {};".format(table_name, table_name, row_id[0], row_id[0])
                db.execute(query)
                db.commit()
            else:
                print("IT WAS A LOSS.")
                query = "UPDATE {} " \
                        "SET losses = " \
                        "(SELECT losses FROM {} WHERE id = {}) + 1 " \
                        "WHERE id = {};".format(table_name, table_name, row_id[0], row_id[0])
                db.execute(query)
                db.commit()
        else:
            print("CREATING A NEW ROW.")
            # there is no row, it has to be created
            query = "SELECT id FROM decks WHERE name = '{}' OR name = '{}';".format(player_deck, enemy_deck)
            cur = db.execute(query)
            ids = cur.fetchall()
            player_id = ids[0][0]
            if len(ids) is 1:
                enemy_id = player_id
            else:
                enemy_id = ids[1][0]

            print("PLAYER IDS: " + str(player_id) + " " + str(enemy_id))

            if win == "win":
                print("IT WAS A WIN.")
                query = "INSERT INTO {} " \
                        "VALUES (NULL, {}, {}, 1, 0);".format(table_name, player_id, enemy_id)
                db.execute(query)
                db.commit()
            else:
                print("IT WAS A LOSS.")
                query = "INSERT INTO {} " \
                        "VALUES (NULL, {}, {}, 0, 1);".format(table_name, player_id, enemy_id)
                db.execute(query)
                db.commit()

        flash("Game was successfully added.")
        return redirect(url_for("show_entries"))

    return render_template("add_game.html", decks=decks)


def get_all_deck_info():
    db = get_db()
    query = "SELECT name FROM decks;"
    cur = db.execute(query)
    deck_names = cur.fetchall()
    deck_info = []
    for name in deck_names:
        deck_info.append(get_deck_info(name[0]))

    return deck_info


def get_deck_info(deck_name):
    table_name = "d_" + deck_name.replace(" ", "_")
    db = get_db()
    query = "SELECT d1.name AS player, d2.name AS enemy, wins, losses, " \
            "SUM(wins) AS sumwins, SUM(losses) AS sumlosses, d1.class AS class " \
            "FROM {} " \
            "LEFT JOIN decks d1 ON ({}.player = d1.id) " \
            "LEFT JOIN decks d2 on ({}.enemy = d2.id);".format(table_name, table_name, table_name)
    cur = db.execute(query)
    deck_info = cur.fetchall()
    # @TODO: aggregate and format data
    return deck_info
    # print(deck_info)


def get_db():
    if not hasattr(g, "db"):
        g.db = connect_db()
    return g.db


@app.teardown_appcontext
def close_db(error):
    if hasattr(g, "db"):
        g.db.close()


def init_db():
    db = get_db()
    with app.open_resource("schema.sql", mode="r") as db_schema:
        db.cursor().executescript(db_schema.read())
    db.commit()


@app.cli.command("initdb")
def init_db_command():
    init_db()
    print("Initialized the production database.")


def connect_db():
    rv = sqlite3.connect(app.config["DATABASE"])
    rv.row_factory = sqlite3.Row
    return rv

if __name__ == '__main__':
    app.run()
