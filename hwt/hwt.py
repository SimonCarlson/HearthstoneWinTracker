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
    messages = "hello"
    query = "SELECT name FROM decks;"
    db = get_db()
    cur = db.execute(query)
    deck_info = cur.fetchall()
    return render_template("show_entries.html", messages=messages, deck_info=deck_info)


@app.route("/add_deck", methods=["GET", "POST"])
def add_deck():
    error = None
    classes = ["Druid", "Hunter", "Mage", "Paladin", "Priest", "Rogue", "Shaman", "Warlock", "Warrior"]

    if request.method == "POST":
        db = get_db()
        query = "INSERT INTO decks (name, class) VALUES (?, ?)"
        try:
            db.execute(query, [request.form["deck_name"], request.form["class_name"]])
            db.commit()
            # @TODO: figure out how to exchange table name to a ?
            tablename = "d_" + request.form["deck_name"].replace(" ", "_")
            query = "CREATE TABLE {} (" \
                    "id INTEGER PRIMARY KEY AUTOINCREMENT," \
                    "player INTEGER REFERENCES decks(id)," \
                    "enemy INTEGER REFERENCES decks(id)," \
                    "wins INTEGER," \
                    "losses INTEGER" \
                    ")".format(tablename)
            db.execute(query)
            db.commit()
            flash("Deck was successfully added.")
            return redirect(url_for("show_entries"))
        except sqlite3.IntegrityError as e:
            #print("Integrity error.")
            flash("A deck with that name already exists.")


    return render_template("add_deck.html", error=error, classes=classes)


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
