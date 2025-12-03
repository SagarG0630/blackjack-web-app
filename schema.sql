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

CREATE TABLE action_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL,
    action       TEXT NOT NULL,              -- 'login', 'hit', 'stand', 'new_game', etc.
    details      TEXT,                       
    created_at   TEXT DEFAULT (CURRENT_TIMESTAMP)
);
