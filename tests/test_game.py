# tests/test_game.py
from app import Card, Deck, hand_value, BlackjackGame


def test_card_value():
    card = Card("K", "hearts")
    assert card.value() == 10

    ace = Card("A", "spades")
    assert ace.value() == 11


def test_deck_has_52_unique_cards():
    deck = Deck()
    assert len(deck.cards) == 52

    dealt = set()
    while deck.cards:
        card = deck.deal()
        card_repr = (card.rank, card.suit)
        assert card_repr not in dealt
        dealt.add(card_repr)

    assert len(dealt) == 52


def test_hand_value_without_aces():
    cards = [Card("10", "hearts"), Card("9", "spades")]
    assert hand_value(cards) == 19


def test_hand_value_with_single_ace():
    cards = [Card("A", "hearts"), Card("9", "spades")]
    assert hand_value(cards) == 20


def test_hand_value_with_ace_adjustment():
    # A + 9 + K = 11 + 9 + 10 = 30 -> adjust Ace to 1 => 20
    cards = [Card("A", "hearts"), Card("9", "spades"), Card("K", "clubs")]
    assert hand_value(cards) == 20


def test_blackjack_game_start():
    game = BlackjackGame()
    game.start()

    assert len(game.player_cards) == 2
    assert len(game.dealer_cards) == 2
    assert game.finished is False
    assert "Game started" in game.message


def test_player_hit_and_busts(monkeypatch):
    # Make a deck that causes player to bust on hit
    game = BlackjackGame()

    # Force known cards
    game.player_cards = [Card("K", "hearts"), Card("9", "spades")]  # total 19
    game.dealer_cards = [Card("2", "clubs"), Card("3", "diamonds")]

    # Next dealt card will be a 5 -> 24 bust
    class FakeDeck:
        def __init__(self):
            self.cards = [Card("5", "hearts")]

        def deal(self):
            return self.cards.pop()

    game.deck = FakeDeck()

    game.finished = False
    game.player_hit()
    assert game.finished is True
    assert "busted" in game.message


def test_player_stand_dealer_busts():
    game = BlackjackGame()

    # Player has 18
    game.player_cards = [Card("10", "hearts"), Card("8", "spades")]

    # Dealer starts low so they must draw
    game.dealer_cards = [Card("2", "clubs"), Card("3", "diamonds")]

    # Custom deck so dealer draws and busts
    class FakeDeck:
        def __init__(self):
            # dealer draws 10 and K -> total > 21
            self.cards = [Card("K", "hearts"), Card("10", "spades")]

        def deal(self):
            return self.cards.pop()

    game.deck = FakeDeck()
    game.finished = False

    game.player_stand()
    assert game.finished is True
    assert "You win" in game.message or "win" in game.message
