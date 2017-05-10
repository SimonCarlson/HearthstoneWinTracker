import os
import sqlite3
import re
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
            # scrub the name
            # if it doesnt' work, abort and notify user
            table_name = get_table_name(request.form["deck_name"])
            scrub_table_name(table_name)

            db.execute(query, [request.form["deck_name"], request.form["class_name"]])

            query = "CREATE TABLE {} (" \
                    "id INTEGER PRIMARY KEY AUTOINCREMENT," \
                    "player INTEGER REFERENCES decks(id) ON DELETE CASCADE," \
                    "enemy INTEGER REFERENCES decks(id) ON DELETE CASCADE," \
                    "wins INTEGER DEFAULT 0," \
                    "losses INTEGER DEFAULT 0" \
                    ")".format(table_name)
            db.execute(query)
            db.commit()
            flash("Deck was successfully added.")
            return redirect(url_for("show_entries"))
        except NameError:
            flash("Invalid deck name. Only use alphabetical characters, numbers and whitespaces.")
        except sqlite3.IntegrityError:
            flash("A deck with that name already exists.")
        except sqlite3.Error:
            flash("Something went wrong. Try again.")

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
        win = request.form["win"]
        table_name = get_table_name(request.form["player_deck"])
        try:
            scrub_table_name(table_name)
            scrub_table_name(player_deck)
            scrub_table_name(enemy_deck)
        except NameError:
            flash("Invalid deck name. Only use alphabetical characters, numbers and whitespaces.")
            return render_template("add_game.html", decks=decks)

        # get the primary key of the matchup
        query = "SELECT id FROM {} " \
                "WHERE player = " \
                "(SELECT id FROM decks WHERE name = ?) " \
                "AND enemy = " \
                "(SELECT id FROM decks WHERE name = ?);".format(table_name)
        cur = db.execute(query, [player_deck, enemy_deck])
        row_id = cur.fetchone()

        if row_id is not None:
            # there is a row for that player deck and enemy deck, update it
            if win == "win":
                query = "UPDATE {} " \
                        "SET wins = " \
                        "(SELECT wins FROM {} WHERE id = ?) + 1 " \
                        "WHERE id = ?;".format(table_name, table_name)
            else:
                query = "UPDATE {} " \
                        "SET losses = " \
                        "(SELECT losses FROM {} WHERE id = ?) + 1 " \
                        "WHERE id = ?;".format(table_name, table_name)

            db.execute(query, [row_id[0], row_id[0]])
            db.commit()
        else:
            # there is no row, it has to be created
            try:
                # @TODO: get both ids in one query?
                query = "SELECT id FROM decks WHERE name = '{}';".format(player_deck)
                cur = db.execute(query)
                ids = cur.fetchone()
                player_id = ids[0]

                query = "SELECT id FROM decks WHERE name = '{}';".format(enemy_deck)
                cur = db.execute(query)
                ids = cur.fetchone()
                enemy_id = ids[0]
            except TypeError:
                flash("Invalid deck names were provided. Try again.")
                return render_template("add_game.html", decks=decks)

            if win == "win":
                query = "INSERT INTO {} " \
                        "VALUES (NULL, ?, ?, 1, 0);".format(table_name)
            else:
                query = "INSERT INTO {} " \
                        "VALUES (NULL, ?, ?, 0, 1);".format(table_name)

            db.execute(query, [player_id, enemy_id])
            db.commit()

        flash("Game was successfully added.")
        return redirect(url_for("show_entries"))

    return render_template("add_game.html", decks=decks)


@app.route("/delete_deck", methods=["GET", "POST"])
def delete_deck():
    db = get_db()
    query = "SELECT name FROM decks;"
    cur = db.execute(query)
    decks = cur.fetchall()

    if request.method == "POST":
        table_name = get_table_name(request.form["deck_name"])
        try:
            scrub_table_name(table_name)
        except NameError:
            flash("Invalid deck name. Only use alphabetical characters, numbers and whitespaces.")

        query = "DELETE FROM decks " \
                "WHERE name = ?;"
        db.execute(query, [request.form["deck_name"]])

        query = "DROP TABLE {};".format(table_name)
        db.execute(query)
        db.commit()

        flash("Deck was successfully removed.")
        return redirect(url_for("show_entries"))

    return render_template("delete_deck.html", decks=decks)


def scrub_table_name(table_name):
    regex = re.compile("(\w*\s*)*")
    match = regex.match(table_name)
    if match.group() is not table_name:
        raise NameError("Invalid deck name.")


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
    table_name = get_table_name(deck_name)
    try:
        scrub_table_name(table_name)
    except NameError:
        flash("Invalid deck name. Only use alphabetical characters, numbers and whitespaces.")
    db = get_db()

    # gets players total wins and losses
    query = "SELECT SUM(wins) AS wins, SUM(losses) AS losses " \
            "FROM {};".format(table_name)
    cur = db.execute(query)
    temp = cur.fetchone()
    wins = temp["wins"]
    losses = temp["losses"]
    try:
        ratio = round(wins / (wins + losses) * 100, 2)
    except ZeroDivisionError:
        ratio = 100.0
    except TypeError:
        # if there are no wins nor losses there are no matchups recorded
        # in this case, nothing is returned in order to avoid empty templating
        return

    query = "SELECT class " \
            "FROM decks " \
            "WHERE name = '{}'".format(deck_name)
    cur = db.execute(query)
    temp = cur.fetchone()
    class_name = temp["class"]

    # gets opponent name, wins and losses for each matchup
    query = "SELECT d2.name AS enemy, wins, losses, ROUND((1.0 * wins/ (wins + losses)) * 100, 2) AS ratio " \
            "FROM {} " \
            "LEFT JOIN decks d1 ON ({}.player = d1.id) " \
            "LEFT JOIN decks d2 on ({}.enemy = d2.id);".format(table_name, table_name, table_name)
    cur = db.execute(query)
    matchups = cur.fetchall()

    return {"deck_name": deck_name, "class": class_name, "wins": wins, "losses": losses, "ratio": ratio, "matchups": matchups}


def get_table_name(deck_name):
    return "d_" + deck_name.replace(" ", "_")


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
    rv.execute("PRAGMA FOREIGN_KEYS=1")
    rv.row_factory = sqlite3.Row
    return rv

if __name__ == '__main__':
    app.run()
