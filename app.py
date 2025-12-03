from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import random
import os
from functools import wraps
from datetime import datetime

app = Flask(__name__)
app.secret_key = "change-me-for-production"

# This creates a blackjack.db file in the same folder
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Default: local sqlite file in the repo (for dev)
default_sqlite_path = os.path.join(BASE_DIR, "blackjack.db")
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{default_sqlite_path}")

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)  # becomes INTEGER PRIMARY KEY in SQLite
    username = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())


class HandHistory(db.Model):
    __tablename__ = "hand_history"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    result = db.Column(db.String(10), nullable=False)  # 'win', 'loss', 'push'
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())


class ActionLog(db.Model):
    __tablename__ = "action_log"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    action = db.Column(db.String(50), nullable=False)   # 'login', 'hit', 'stand', 'new_game', etc.
    details = db.Column(db.Text)                        # optional JSON/message
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

with app.app_context():
    db.create_all()

# ----------------------------
# Blackjack game logic
# ----------------------------

SUITS = ["hearts", "diamonds", "clubs", "spades"]
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
VALUES = {
    "2": 2,
    "3": 3,
    "4": 4,
    "5": 5,
    "6": 6,
    "7": 7,
    "8": 8,
    "9": 9,
    "10": 10,
    "J": 10,
    "Q": 10,
    "K": 10,
    "A": 11,
}


class Card:
    def __init__(self, rank, suit):
        self.rank = rank
        self.suit = suit

    def value(self):
        return VALUES[self.rank]

    def __repr__(self):
        return f"{self.rank} of {self.suit}"


class Deck:
    def __init__(self):
        self.cards = [Card(rank, suit) for suit in SUITS for rank in RANKS]
        random.shuffle(self.cards)

    def deal(self):
        return self.cards.pop()


def hand_value(cards):
    total = sum(card.value() for card in cards)
    aces = sum(1 for card in cards if card.rank == "A")
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    return total


class BlackjackGame:
    def __init__(self):
        self.deck = Deck()
        self.player_cards = []
        self.dealer_cards = []
        self.finished = False
        self.message = ""

    def start(self):
        self.deck = Deck()
        self.player_cards = [self.deck.deal(), self.deck.deal()]
        self.dealer_cards = [self.deck.deal(), self.deck.deal()]
        self.finished = False
        self.message = "Game started. Hit or stand?"

    def player_hit(self):
        if self.finished:
            return
        self.player_cards.append(self.deck.deal())
        if hand_value(self.player_cards) > 21:
            self.finished = True
            self.message = "You busted! Dealer wins."

    def player_stand(self):
        if self.finished:
            return
        while hand_value(self.dealer_cards) < 17:
            self.dealer_cards.append(self.deck.deal())
        self.finished = True
        player_total = hand_value(self.player_cards)
        dealer_total = hand_value(self.dealer_cards)
        if dealer_total > 21 or player_total > dealer_total:
            self.message = "You win!"
        elif player_total < dealer_total:
            self.message = "Dealer wins."
        else:
            self.message = "Push (tie)."


# one game per logged-in user (in memory)
GAMES = {}  # username -> BlackjackGame


def get_current_user():
    return session.get("user")


def get_game_for_user(username):
    game = GAMES.get(username)
    if game is None:
        game = BlackjackGame()
        game.start()
        GAMES[username] = game
    return game


def format_seconds_hhmmss(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


# ----------------------------
# Auth helpers / decorator
# ----------------------------

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            flash("Please log in to access the game.")
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return wrapper


# ----------------------------
# Auth routes
# ----------------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()

        if not username or not password:
            flash("Username and password are required.")
            return redirect(url_for("register"))

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Username already exists.")
            return redirect(url_for("register"))

        password_hash = generate_password_hash(password)
        user = User(username=username, password_hash=password_hash)
        db.session.add(user)
        db.session.commit()

        flash("Account created! Please log in.")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            # non‑permanent session: cookie expires when browser closes
            session.permanent = False
            session["user"] = user.username
            # start game session timer
            session["session_start"] = datetime.utcnow().isoformat()
            flash("Logged in successfully.")

            # log login action
            log = ActionLog(user_id=user.id, action="login")
            db.session.add(log)
            db.session.commit()

            return redirect(url_for("index"))
        else:
            flash("Invalid username or password.")

    return render_template("login.html")


@app.route("/logout")
def logout():
    username = session.get("user")
    user = User.query.filter_by(username=username).first() if username else None
    if user:
        log = ActionLog(user_id=user.id, action="logout")
        db.session.add(log)
        db.session.commit()

    session.pop("user", None)
    session.pop("session_start", None)
    flash("You have been logged out.")
    return redirect(url_for("login"))


# ----------------------------
# Game routes
# ----------------------------

@app.route("/")
@login_required
def index():
    username = get_current_user()
    game = get_game_for_user(username)

    user = User.query.filter_by(username=username).first()
    wins = losses = pushes = 0
    if user:
        wins = HandHistory.query.filter_by(user_id=user.id, result="win").count()
        losses = HandHistory.query.filter_by(user_id=user.id, result="loss").count()
        pushes = HandHistory.query.filter_by(user_id=user.id, result="push").count()

    # session timer
    session_time = "00:00:00"
    start_str = session.get("session_start")
    if start_str:
        start = datetime.fromisoformat(start_str)
        elapsed = int((datetime.utcnow() - start).total_seconds())
        if elapsed < 0:
            elapsed = 0
        session_time = format_seconds_hhmmss(elapsed)

    return render_template(
        "index.html",
        user=username,
        player_cards=game.player_cards,
        dealer_cards=game.dealer_cards,
        player_total=hand_value(game.player_cards),
        dealer_total=hand_value(game.dealer_cards),
        message=game.message,
        finished=game.finished,
        wins=wins,
        losses=losses,
        pushes=pushes,
        session_time=session_time,
    )


@app.route("/hit")
@login_required
def hit():
    username = get_current_user()
    game = get_game_for_user(username)
    game.player_hit()

    user = User.query.filter_by(username=username).first()

    # log action
    if user:
        log = ActionLog(user_id=user.id, action="hit")
        db.session.add(log)

    # if bust on hit, log a loss
    if game.finished and "busted" in game.message and user:
        record = HandHistory(user_id=user.id, result="loss")
        db.session.add(record)

    if user:
        db.session.commit()

    return redirect(url_for("index"))


@app.route("/stand")
@login_required
def stand():
    username = get_current_user()
    game = get_game_for_user(username)
    game.player_stand()

    user = User.query.filter_by(username=username).first()

    if user:
        # log stand action
        log = ActionLog(user_id=user.id, action="stand")
        db.session.add(log)

    # log result based on final message
    if user and game.finished:
        if "You win" in game.message:
            result = "win"
        elif "Dealer wins" in game.message or "busted" in game.message:
            result = "loss"
        else:
            result = "push"

        record = HandHistory(user_id=user.id, result=result)
        db.session.add(record)

    if user:
        db.session.commit()

    return redirect(url_for("index"))


@app.route("/new")
@login_required
def new_game():
    username = get_current_user()
    game = get_game_for_user(username)
    game.start()

    user = User.query.filter_by(username=username).first()
    if user:
        log = ActionLog(user_id=user.id, action="new_game")
        db.session.add(log)
        db.session.commit()

    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run()  # no debug=True here
