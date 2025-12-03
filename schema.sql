-- Users table
CREATE TABLE public.users (
    id          SERIAL PRIMARY KEY,
    username    VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Hand history table
CREATE TABLE public.hand_history (
    id           SERIAL PRIMARY KEY,
    user_id      INT NOT NULL,
    game_id      INT NOT NULL,
    hand_number  INT NOT NULL,
    timestamp    TIMESTAMPTZ DEFAULT NOW(),
    result       VARCHAR(10) NOT NULL,
    bet_amount   NUMERIC(10,2),
    winnings     NUMERIC(10,2),
    player_hand  VARCHAR(100),
    dealer_hand  VARCHAR(100)
);
