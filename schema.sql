CREATE TABLE users (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    username     TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at   TEXT DEFAULT (CURRENT_TIMESTAMP)
);

CREATE TABLE hand_history (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL,
    game_id      INTEGER NOT NULL,
    hand_number  INTEGER NOT NULL,
    timestamp    TEXT DEFAULT (CURRENT_TIMESTAMP),
    result       TEXT NOT NULL,
    bet_amount   REAL,
    winnings     REAL,
    player_hand  TEXT,
    dealer_hand  TEXT
);
