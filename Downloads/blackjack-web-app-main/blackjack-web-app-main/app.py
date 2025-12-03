from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import random
import os
from functools import wraps
from datetime import datetime, timedelta
from collections import defaultdict

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
# Operational Dashboard Helper Functions
# ----------------------------

def get_system_overview():
    """Get system-wide operational metrics"""
    now = datetime.utcnow()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)
    last_30d = now - timedelta(days=30)
    
    return {
        # User metrics
        'total_users': User.query.count(),
        'new_users_today': User.query.filter(User.created_at >= today).count(),
        'new_users_7d': User.query.filter(User.created_at >= last_7d).count(),
        'new_users_30d': User.query.filter(User.created_at >= last_30d).count(),
        'active_users_24h': len(set([
            log.user_id for log in ActionLog.query.filter(
                ActionLog.action == 'login',
                ActionLog.created_at >= last_24h
            ).all()
        ])),
        
        # Game metrics
        'total_games': HandHistory.query.count(),
        'games_today': HandHistory.query.filter(HandHistory.created_at >= today).count(),
        'games_24h': HandHistory.query.filter(HandHistory.created_at >= last_24h).count(),
        'games_7d': HandHistory.query.filter(HandHistory.created_at >= last_7d).count(),
        'games_30d': HandHistory.query.filter(HandHistory.created_at >= last_30d).count(),
        
        # Action metrics
        'total_actions': ActionLog.query.count(),
        'logins_today': ActionLog.query.filter(
            ActionLog.action == 'login',
            ActionLog.created_at >= today
        ).count(),
        'logins_7d': ActionLog.query.filter(
            ActionLog.action == 'login',
            ActionLog.created_at >= last_7d
        ).count(),
    }


def get_daily_activity(days=30):
    """Get daily activity trends for last N days"""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Games per day
    games = HandHistory.query.filter(
        HandHistory.created_at >= start_date
    ).all()
    
    games_by_day = defaultdict(int)
    for game in games:
        day = game.created_at.date()
        games_by_day[day] += 1
    
    # Users per day
    users = User.query.filter(
        User.created_at >= start_date
    ).all()
    
    users_by_day = defaultdict(int)
    for user in users:
        day = user.created_at.date()
        users_by_day[day] += 1
    
    # Logins per day
    logins = ActionLog.query.filter(
        ActionLog.action == 'login',
        ActionLog.created_at >= start_date
    ).all()
    
    logins_by_day = defaultdict(int)
    for login in logins:
        day = login.created_at.date()
        logins_by_day[day] += 1
    
    # Combine into list of daily stats
    daily_stats = []
    current_date = start_date.date()
    end_date_only = end_date.date()
    
    while current_date <= end_date_only:
        daily_stats.append({
            'date': current_date,
            'games': games_by_day.get(current_date, 0),
            'new_users': users_by_day.get(current_date, 0),
            'logins': logins_by_day.get(current_date, 0)
        })
        current_date += timedelta(days=1)
    
    return daily_stats


def get_action_distribution():
    """Get distribution of actions by type"""
    from sqlalchemy import func
    
    results = ActionLog.query.with_entities(
        ActionLog.action,
        func.count(ActionLog.id).label('count')
    ).group_by(ActionLog.action).all()
    
    return {action: count for action, count in results}


def get_most_active_users(limit=10):
    """Get most active users by game count"""
    from sqlalchemy import func
    
    results = HandHistory.query.with_entities(
        HandHistory.user_id,
        func.count(HandHistory.id).label('game_count')
    ).group_by(HandHistory.user_id)\
     .order_by(func.count(HandHistory.id).desc())\
     .limit(limit).all()
    
    active_users = []
    for user_id, game_count in results:
        user = User.query.get(user_id)
        if user:
            active_users.append({
                'username': user.username,
                'game_count': game_count,
                'user_id': user_id
            })
    
    return active_users


def get_hourly_activity():
    """Get activity by hour of day (last 7 days)"""
    last_7d = datetime.utcnow() - timedelta(days=7)
    
    games = HandHistory.query.filter(
        HandHistory.created_at >= last_7d
    ).all()
    
    games_by_hour = defaultdict(int)
    for game in games:
        hour = game.created_at.hour
        games_by_hour[hour] += 1
    
    logins = ActionLog.query.filter(
        ActionLog.action == 'login',
        ActionLog.created_at >= last_7d
    ).all()
    
    logins_by_hour = defaultdict(int)
    for login in logins:
        hour = login.created_at.hour
        logins_by_hour[hour] += 1
    
    hourly_stats = []
    for hour in range(24):
        hourly_stats.append({
            'hour': hour,
            'games': games_by_hour.get(hour, 0),
            'logins': logins_by_hour.get(hour, 0)
        })
    
    return hourly_stats


def get_system_health():
    """Get system health status"""
    try:
        # Test database connection with a simple query
        User.query.count()
        db_status = 'connected'
    except:
        db_status = 'disconnected'
    
    # Calculate average games per user
    total_users = User.query.count()
    total_games = HandHistory.query.count()
    avg_games_per_user = (total_games / total_users) if total_users > 0 else 0
    
    # Calculate overall win rate
    total_games = HandHistory.query.count()
    wins = HandHistory.query.filter_by(result='win').count()
    overall_win_rate = (wins / total_games * 100) if total_games > 0 else 0
    
    return {
        'database_status': db_status,
        'total_records': {
            'users': User.query.count(),
            'games': HandHistory.query.count(),
            'actions': ActionLog.query.count()
        },
        'avg_games_per_user': round(avg_games_per_user, 2),
        'overall_win_rate': round(overall_win_rate, 1)
    }


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
            # nonΓÇæpermanent session: cookie expires when browser closes
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


# ----------------------------
# Dashboard route
# ----------------------------

@app.route("/dashboard")
@login_required
def dashboard():
    """Operational dashboard showing system metrics and activity"""
    # Get all operational metrics
    overview = get_system_overview()
    daily_activity = get_daily_activity(days=30)
    action_dist = get_action_distribution()
    active_users = get_most_active_users(limit=10)
    hourly_activity = get_hourly_activity()
    system_health = get_system_health()
    
    return render_template(
        "dashboard.html",
        overview=overview,
        daily_activity=daily_activity,
        action_distribution=action_dist,
        active_users=active_users,
        hourly_activity=hourly_activity,
        system_health=system_health
    )


if __name__ == "__main__":
    app.run(debug=True)
