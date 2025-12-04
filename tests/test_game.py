# tests/test_game.py

from app import (
    Card,
    Deck,
    BlackjackGame,
    hand_value,
    format_seconds_hhmmss,
    get_game_for_user,
    GAMES,
)


def test_card_value_and_repr():
    card = Card("A", "hearts")
    assert card.value() == 11
    assert "A of hearts" in repr(card)


def test_deck_has_52_unique_cards():
    deck = Deck()
    assert len(deck.cards) == 52

    dealt = [deck.deal() for _ in range(52)]
    ranks_suits = {(c.rank, c.suit) for c in dealt}
    assert len(ranks_suits) == 52

    # Deck should now be empty
    assert deck.cards == []


def test_hand_value_no_aces():
    cards = [Card("10", "hearts"), Card("9", "spades")]
    assert hand_value(cards) == 19


def test_hand_value_single_ace_adjustment():
    cards = [Card("A", "hearts"), Card("9", "spades")]
    # 11 + 9 = 20, no need to adjust
    assert hand_value(cards) == 20

    cards = [Card("A", "hearts"), Card("9", "spades"), Card("5", "clubs")]
    # 11 + 9 + 5 = 25 -> adjust Ace to 1 -> 15
    assert hand_value(cards) == 15


def test_hand_value_multiple_aces():
    cards = [Card("A", "hearts"), Card("A", "spades"), Card("9", "clubs")]
    # 11 + 11 + 9 = 31 -> adjust one Ace -> 21
    assert hand_value(cards) == 21

    cards = [Card("A", "hearts"), Card("A", "spades"), Card("A", "clubs"), Card("9", "diamonds")]
    # 11 + 11 + 11 + 9 = 42 -> adjust down as needed -> 12
    assert hand_value(cards) == 12


def test_blackjack_game_start_initializes_state():
    game = BlackjackGame()
    game.start()

    assert len(game.player_cards) == 2
    assert len(game.dealer_cards) == 2
    assert game.finished is False
    assert "Hit or stand" in game.message


def test_blackjack_game_player_hit_busts():
    # Create a rigged game where player will bust
    game = BlackjackGame()
    # Manually set up deck and hand
    game.deck.cards = [
        Card("10", "hearts"),
    ]  # next dealt card -> 10
    game.player_cards = [Card("K", "clubs"), Card("8", "spades")]  # 10 + 8 = 18
    game.dealer_cards = [Card("2", "hearts"), Card("3", "spades")]

    game.player_hit()
    assert game.finished is True
    assert "busted" in game.message


def test_blackjack_game_player_stand_resolves_game():
    game = BlackjackGame()
    game.start()
    # Force a deterministic game: player has 20, dealer has 18
    game.player_cards = [Card("K", "clubs"), Card("Q", "hearts")]  # 20
    game.dealer_cards = [Card("9", "clubs"), Card("9", "hearts")]  # 18

    game.player_stand()
    assert game.finished is True
    assert "You win" in game.message or "Dealer wins" in game.message or "Push" in game.message


def test_get_game_for_user_creates_and_reuses_game():
    username = "testuser"
    # Ensure clean
    GAMES.clear()

    game1 = get_game_for_user(username)
    assert username in GAMES
    assert isinstance(game1, BlackjackGame)

    game2 = get_game_for_user(username)
    assert game1 is game2  # same game object reused


def test_format_seconds_hhmmss():
    assert format_seconds_hhmmss(0) == "00:00:00"
    assert format_seconds_hhmmss(59) == "00:00:59"
    assert format_seconds_hhmmss(60) == "00:01:00"
    assert format_seconds_hhmmss(3661) == "01:01:01"
