DROP TABLE IF EXISTS decks;
CREATE TABLE decks(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE ON CONFLICT ABORT,
  class TEXT NOT NULL
);