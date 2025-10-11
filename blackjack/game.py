import random

# Function to create a deck
def create_deck():
    suits = ['Hearts', 'Diamonds', 'Clubs', 'Spades']
    ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
    deck = [{'rank': rank, 'suit': suit} for suit in suits for rank in ranks]
    random.shuffle(deck)
    return deck

# Function to calculate hand value
def calculate_hand_value(hand):
    value = 0
    aces = 0
    for card in hand:
        if card['rank'] in ['J', 'Q', 'K']:
            value += 10
        elif card['rank'] == 'A':
            value += 11
            aces += 1
        else:
            value += int(card['rank'])
    # Adjust for aces
    while value > 21 and aces:
        value -= 10
        aces -= 1
    return value

# Function to display hand
def display_hand(hand, name):
    cards = ', '.join(f"{card['rank']} of {card['suit']}" for card in hand)
    print(f"{name}'s hand: {cards} (Value: {calculate_hand_value(hand)})")

# Game logic
def blackjack():
    deck = create_deck()
    
    player_hand = [deck.pop(), deck.pop()]
    dealer_hand = [deck.pop(), deck.pop()]
    
    # Show initial hands
    display_hand(player_hand, "Player")
    print(f"Dealer's hand: {dealer_hand[0]['rank']} of {dealer_hand[0]['suit']} and [Hidden]")

    # Player's turn
    while True:
        move = input("Do you want to Hit or Stand? (h/s): ").lower()
        if move == 'h':
            player_hand.append(deck.pop())
            display_hand(player_hand, "Player")
            if calculate_hand_value(player_hand) > 21:
                print("You busted! Dealer wins.")
                return
        elif move == 's':
            break
        else:
            print("Invalid input. Please enter 'h' or 's'.")
    
    # Dealer's turn
    print("\nDealer reveals hand:")
    display_hand(dealer_hand, "Dealer")
    
    while calculate_hand_value(dealer_hand) < 17:
        dealer_hand.append(deck.pop())
        display_hand(dealer_hand, "Dealer")
        if calculate_hand_value(dealer_hand) > 21:
            print("Dealer busted! You win!")
            return
    
    # Compare hands
    player_value = calculate_hand_value(player_hand)
    dealer_value = calculate_hand_value(dealer_hand)
    
    if player_value > dealer_value:
        print("You win!")
    elif player_value < dealer_value:
        print("Dealer wins!")
    else:
        print("It's a tie!")

# Run the game
if __name__ == "__main__":
    blackjack()
