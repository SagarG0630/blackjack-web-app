from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import random
import os
import subprocess
import json
import xml.etree.ElementTree as ET
from functools import wraps
from datetime import datetime, timedelta
from collections import defaultdict

app = Flask(__name__)
app.secret_key = "change-me-for-production"

# Base dir where app.py lives
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

DB_DIR = os.environ.get("DB_DIR", BASE_DIR)

# Default SQLite path (persistent)
default_sqlite_path = os.path.join(DB_DIR, "blackjack.db")

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
# User Dashboard Helper Functions (Gameplay Stats)
# ----------------------------

def get_user_statistics(user_id):
    """Get gameplay statistics for a specific user"""
    total_games = HandHistory.query.filter_by(user_id=user_id).count()
    wins = HandHistory.query.filter_by(user_id=user_id, result='win').count()
    losses = HandHistory.query.filter_by(user_id=user_id, result='loss').count()
    pushes = HandHistory.query.filter_by(user_id=user_id, result='push').count()
    
    win_rate = (wins / total_games * 100) if total_games > 0 else 0
    
    return {
        'total_games': total_games,
        'wins': wins,
        'losses': losses,
        'pushes': pushes,
        'win_rate': round(win_rate, 1)
    }


def get_recent_games(user_id, limit=10):
    """Get recent games for a user"""
    return HandHistory.query.filter_by(user_id=user_id)\
        .order_by(HandHistory.created_at.desc())\
        .limit(limit).all()


def get_user_game_history(user_id, days=30):
    """Get user's game history by day"""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    games = HandHistory.query.filter(
        HandHistory.user_id == user_id,
        HandHistory.created_at >= start_date
    ).all()
    
    games_by_day = defaultdict(int)
    for game in games:
        day = game.created_at.date()
        games_by_day[day] += 1
    
    # Create list of daily stats
    daily_stats = []
    current_date = start_date.date()
    end_date_only = end_date.date()
    
    while current_date <= end_date_only:
        daily_stats.append({
            'date': current_date,
            'games': games_by_day.get(current_date, 0)
        })
        current_date += timedelta(days=1)
    
    return daily_stats


# ----------------------------
# Operational Dashboard Helper Functions (Admin Only)
# ----------------------------

def get_system_overview():
    """Get system-wide operational metrics"""
    now = datetime.utcnow()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)
    last_30d = now - timedelta(days=30)
    
    return {
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
        'total_games': HandHistory.query.count(),
        'games_today': HandHistory.query.filter(HandHistory.created_at >= today).count(),
        'games_24h': HandHistory.query.filter(HandHistory.created_at >= last_24h).count(),
        'games_7d': HandHistory.query.filter(HandHistory.created_at >= last_7d).count(),
        'games_30d': HandHistory.query.filter(HandHistory.created_at >= last_30d).count(),
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
    
    total_users = User.query.count()
    total_games = HandHistory.query.count()
    avg_games_per_user = (total_games / total_users) if total_users > 0 else 0
    
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


def is_admin(user):
    """Check if user is admin"""
    if not user:
        return False
    admin_users = os.environ.get('ADMIN_USERS', 'admin').split(',')
    return user.username in admin_users or user.username == 'admin'


def admin_required(f):
    """Decorator to require admin privileges"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            flash("Please log in to access admin dashboard.")
            return redirect(url_for("login"))
        user = User.query.filter_by(username=session['user']).first()
        if not is_admin(user):
            flash("Access denied. Admin privileges required.")
            return redirect(url_for("index"))
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
# Admin Dashboard Helper Functions (DevOps Metrics)
# ----------------------------

def get_test_coverage():
    """Get current test coverage percentage"""
    try:
        # Try to read coverage.xml if it exists (fastest method)
        if os.path.exists('coverage.xml'):
            try:
                tree = ET.parse('coverage.xml')
                root = tree.getroot()
                # Find line-rate attribute
                line_rate = float(root.get('line-rate', 0))
                return round(line_rate * 100, 2)
            except (ET.ParseError, ValueError, AttributeError):
                pass
        
        # Skip subprocess calls in production/runtime - too slow
        # Only read from existing files
        return None
    except Exception:
        # Silently fail - don't break dashboard
        return None


def get_test_results():
    """Get latest test run results - only reads from existing files, no subprocess calls"""
    try:
        # Try to read JSON report if it exists (fastest method)
        if os.path.exists('test-report.json'):
            try:
                with open('test-report.json', 'r') as f:
                    report = json.load(f)
                    return {
                        'total': report.get('summary', {}).get('total', 0),
                        'passed': report.get('summary', {}).get('passed', 0),
                        'failed': report.get('summary', {}).get('failed', 0),
                        'skipped': report.get('summary', {}).get('skipped', 0),
                        'duration': report.get('duration', 0),
                        'exitcode': report.get('exitcode', 0),
                        'last_run': datetime.utcnow().isoformat()
                    }
            except (json.JSONDecodeError, IOError, KeyError):
                pass
        
        # Skip subprocess calls in production/runtime - too slow
        # Only read from existing files
        return None
    except Exception:
        # Silently fail - don't break dashboard
        return None


def get_security_metrics():
    """Get security metrics from ActionLog"""
    now = datetime.utcnow()
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)
    last_30d = now - timedelta(days=30)
    
    # Failed login attempts (assuming failed logins might be logged differently)
    # For now, we'll track login attempts
    logins_24h = ActionLog.query.filter(
        ActionLog.action == 'login',
        ActionLog.created_at >= last_24h
    ).count()
    
    logins_7d = ActionLog.query.filter(
        ActionLog.action == 'login',
        ActionLog.created_at >= last_7d
    ).count()
    
    secret_key_secure = app.secret_key != "change-me-for-production"
    https_enforced = os.environ.get('HTTPS_ENFORCED', 'false').lower() == 'true'
    
    return {
        'logins_24h': logins_24h,
        'logins_7d': logins_7d,
        'secret_key_secure': secret_key_secure,
        'https_enforced': https_enforced,
        'using_orm': True,  # We use SQLAlchemy ORM
        'xss_protected': True,  # Jinja2 auto-escapes
    }


def get_ci_cd_status():
    """Get CI/CD pipeline status (simplified - can be enhanced with GitHub API)"""
    is_ci = os.environ.get('CI', 'false').lower() == 'true'
    github_actions = os.environ.get('GITHUB_ACTIONS', 'false').lower() == 'true'
    
    has_coverage_xml = os.path.exists('coverage.xml')
    has_test_report = os.path.exists('test-report.json')
    
    return {
        'is_ci': is_ci,
        'github_actions': github_actions,
        'has_coverage': has_coverage_xml,
        'has_test_report': has_test_report,
        'last_check': datetime.utcnow().isoformat()
    }


def get_performance_metrics():
    """Get application performance metrics"""
    total_users = User.query.count()
    total_games = HandHistory.query.count()
    total_actions = ActionLog.query.count()
    
    avg_games_per_user = (total_games / total_users) if total_users > 0 else 0
    
    last_hour = datetime.utcnow() - timedelta(hours=1)
    games_last_hour = HandHistory.query.filter(
        HandHistory.created_at >= last_hour
    ).count()
    
    actions_last_hour = ActionLog.query.filter(
        ActionLog.created_at >= last_hour
    ).count()
    
    return {
        'total_users': total_users,
        'total_games': total_games,
        'total_actions': total_actions,
        'avg_games_per_user': round(avg_games_per_user, 2),
        'games_last_hour': games_last_hour,
        'actions_last_hour': actions_last_hour,
        'activity_rate': round(actions_last_hour / 60, 2) if actions_last_hour > 0 else 0  # per minute
    }


def get_code_quality_metrics():
    """Get code quality metrics - optimized to avoid slow directory walking"""
    try:
        # Limit directory walking to avoid performance issues
        # Only check common directories, not entire tree
        python_files = []
        dirs_to_check = ['app.py', 'tests']
        
        for item in dirs_to_check:
            if os.path.isfile(item) and item.endswith('.py'):
                python_files.append(item)
            elif os.path.isdir(item):
                try:
                    for root, dirs, files in os.walk(item):
                        # Skip hidden dirs and cache
                        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__']]
                        for file in files:
                            if file.endswith('.py'):
                                python_files.append(os.path.join(root, file))
                except (OSError, PermissionError):
                    pass
        
        # Count lines (limit to avoid slow I/O)
        total_lines = 0
        test_lines = 0
        max_files = 50  # Limit to prevent slow operations
        
        for file_path in python_files[:max_files]:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    total_lines += len(lines)
                    if 'test' in file_path.lower():
                        test_lines += len(lines)
            except (UnicodeDecodeError, IOError, OSError):
                pass
        
        # If we hit the limit, estimate
        if len(python_files) > max_files:
            total_lines = int(total_lines * (len(python_files) / max_files))
        
        return {
            'total_files': len(python_files),
            'total_lines': total_lines,
            'test_lines': test_lines,
            'code_to_test_ratio': round((total_lines - test_lines) / test_lines, 2) if test_lines > 0 else 0
        }
    except Exception:
        return {
            'total_files': 0,
            'total_lines': 0,
            'test_lines': 0,
            'code_to_test_ratio': 0
        }


def get_infrastructure_health():
    """Get infrastructure health metrics"""
    try:
        # Test database connection
        User.query.count()
        db_status = 'connected'
    except:
        db_status = 'disconnected'
    
    python_version = f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}"
    
    db_url = os.environ.get('DATABASE_URL', '')
    if 'postgresql' in db_url.lower():
        db_type = 'PostgreSQL'
    elif 'sqlite' in db_url.lower():
        db_type = 'SQLite'
    else:
        db_type = 'SQLite (default)'
    
    environment = os.environ.get('FLASK_ENV', 'development')
    if environment == 'production' or 'FLY_APP_NAME' in os.environ:
        environment = 'production'
    else:
        environment = 'development'
    
    return {
        'database_status': db_status,
        'database_type': db_type,
        'python_version': python_version,
        'flask_version': '3.1.2',  # From requirements
        'environment': environment,
        'is_production': environment == 'production'
    }


def get_security_score():
    """Calculate overall security score (0-100)"""
    score = 0
    max_score = 100
    issues = []
    
    if app.secret_key != "change-me-for-production":
        score += 30
    else:
        issues.append("Secret key is insecure (using default)")
    
    https_enforced = os.environ.get('HTTPS_ENFORCED', 'false').lower() == 'true'
    flask_env = os.environ.get('FLASK_ENV', app.config.get('ENV', 'development'))
    is_production = flask_env == 'production' or 'FLY_APP_NAME' in os.environ
    if https_enforced or is_production:
        score += 20
    else:
        issues.append("HTTPS not enforced in code")
    
    # Using SQLAlchemy for ORM protection
    score += 20
    
    # Jinja2 auto-escapes by default
    score += 20
    
    last_24h = datetime.utcnow() - timedelta(hours=24)
    logins_24h = ActionLog.query.filter(
        ActionLog.action == 'login',
        ActionLog.created_at >= last_24h
    ).count()
    
    if logins_24h < 100:
        score += 10
    else:
        issues.append("Unusual login activity detected")
    
    percentage = round((score / max_score) * 100, 1)
    
    if percentage >= 90:
        grade = 'A'
    elif percentage >= 75:
        grade = 'B'
    elif percentage >= 60:
        grade = 'C'
    elif percentage >= 40:
        grade = 'D'
    else:
        grade = 'F'
    
    return {
        'score': score,
        'max_score': max_score,
        'percentage': percentage,
        'grade': grade,
        'issues': issues
    }


def get_critical_issues():
    """Identify critical issues that need immediate attention"""
    issues = []
    
    if app.secret_key == "change-me-for-production":
        issues.append({
            'severity': 'critical',
            'title': 'Insecure Secret Key',
            'description': 'Secret key is using default value. Session cookies can be forged.',
            'fix': 'Set SECRET_KEY environment variable',
            'time': '5 minutes',
            'file': 'app.py:14'
        })
    
    https_enforced = os.environ.get('HTTPS_ENFORCED', 'false').lower() == 'true'
    flask_env = os.environ.get('FLASK_ENV', app.config.get('ENV', 'development'))
    is_production = flask_env == 'production' or 'FLY_APP_NAME' in os.environ
    if not https_enforced and is_production:
        issues.append({
            'severity': 'high',
            'title': 'HTTPS Not Enforced',
            'description': 'HTTPS enforcement not configured in application code.',
            'fix': 'Add HTTPS redirect in app.py',
            'time': '10 minutes',
            'file': 'app.py'
        })
    
    test_coverage = get_test_coverage()
    if test_coverage is not None and test_coverage < 75:
        issues.append({
            'severity': 'high',
            'title': 'Test Coverage Below 75%',
            'description': f'Current coverage: {test_coverage}%. Target: 75%',
            'fix': 'Add more tests to increase coverage',
            'time': '30+ minutes',
            'file': 'tests/'
        })
    elif test_coverage is None:
        issues.append({
            'severity': 'medium',
            'title': 'Test Coverage Not Available',
            'description': 'Cannot determine test coverage. Run: pytest --cov=. --cov-report=xml',
            'fix': 'Generate coverage report',
            'time': '5 minutes',
            'file': 'tests/'
        })
    
    test_results = get_test_results()
    if test_results and test_results.get('failed', 0) > 0:
        issues.append({
            'severity': 'high',
            'title': f"{test_results['failed']} Test(s) Failing",
            'description': f"{test_results['failed']} out of {test_results['total']} tests are failing.",
            'fix': 'Fix failing tests',
            'time': '30+ minutes',
            'file': 'tests/'
        })
    
    try:
        User.query.count()
    except:
        issues.append({
            'severity': 'critical',
            'title': 'Database Connection Failed',
            'description': 'Cannot connect to database. Application may not function correctly.',
            'fix': 'Check database configuration and connection',
            'time': '15 minutes',
            'file': 'app.py'
        })
    
    return issues


def get_action_items():
    """Generate actionable checklist of issues to fix"""
    issues = get_critical_issues()
    
    action_items = []
    for issue in issues:
        action_items.append({
            'id': len(action_items) + 1,
            'title': issue['title'],
            'severity': issue['severity'],
            'description': issue['description'],
            'fix': issue['fix'],
            'estimated_time': issue['time'],
            'file': issue.get('file', 'N/A'),
            'completed': False
        })
    
    # Sort by severity (critical first)
    severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
    action_items.sort(key=lambda x: severity_order.get(x['severity'], 99))
    
    return action_items


def get_system_health_summary():
    """Get overall system health summary"""
    components = {}
    
    try:
        User.query.count()
        components['database'] = {'status': 'healthy', 'message': 'Connected'}
    except:
        components['database'] = {'status': 'critical', 'message': 'Disconnected'}
    
    security_score = get_security_score()
    if security_score['percentage'] >= 75:
        components['security'] = {'status': 'healthy', 'message': f"Score: {security_score['percentage']}% ({security_score['grade']})"}
    elif security_score['percentage'] >= 50:
        components['security'] = {'status': 'warning', 'message': f"Score: {security_score['percentage']}% ({security_score['grade']})"}
    else:
        components['security'] = {'status': 'critical', 'message': f"Score: {security_score['percentage']}% ({security_score['grade']})"}
    
    test_coverage = get_test_coverage()
    test_results = get_test_results()
    if test_coverage is not None and test_coverage >= 75 and test_results and test_results.get('failed', 0) == 0:
        components['testing'] = {'status': 'healthy', 'message': f"Coverage: {test_coverage}%, All tests passing"}
    elif test_results and test_results.get('failed', 0) > 0:
        components['testing'] = {'status': 'critical', 'message': f"{test_results['failed']} test(s) failing"}
    elif test_coverage is not None and test_coverage < 75:
        components['testing'] = {'status': 'warning', 'message': f"Coverage: {test_coverage}% (below 75%)"}
    else:
        components['testing'] = {'status': 'warning', 'message': 'Test status unknown'}
    
    performance = get_performance_metrics()
    if performance['total_users'] > 0 and performance['total_games'] > 0:
        components['performance'] = {'status': 'healthy', 'message': 'System operational'}
    else:
        components['performance'] = {'status': 'info', 'message': 'No activity yet'}
    
    status_counts = {'healthy': 0, 'warning': 0, 'critical': 0, 'info': 0}
    for comp in components.values():
        status_counts[comp['status']] = status_counts.get(comp['status'], 0) + 1
    
    if status_counts['critical'] > 0:
        overall_status = 'critical'
        overall_message = f"{status_counts['critical']} critical issue(s)"
    elif status_counts['warning'] > 0:
        overall_status = 'warning'
        overall_message = f"{status_counts['warning']} warning(s)"
    else:
        overall_status = 'healthy'
        overall_message = 'All systems operational'
    
    total_components = len(components)
    healthy_count = status_counts['healthy'] + status_counts['info']
    health_score = round((healthy_count / total_components) * 100, 1) if total_components > 0 else 0
    
    return {
        'overall_status': overall_status,
        'overall_message': overall_message,
        'health_score': health_score,
        'components': components,
        'last_check': datetime.utcnow().isoformat()
    }


# ----------------------------
# Dashboard route
# ----------------------------

@app.route("/dashboard")
@login_required
def dashboard():
    """User dashboard showing personal gameplay statistics"""
    username = get_current_user()
    user = User.query.filter_by(username=username).first()
    
    if not user:
        flash("User not found.")
        return redirect(url_for("index"))
    
    stats = get_user_statistics(user.id)
    recent_games = get_recent_games(user.id, limit=10)
    game_history = get_user_game_history(user.id, days=30)
    
    return render_template(
        "dashboard.html",
        user=username,
        stats=stats,
        recent_games=recent_games,
        game_history=game_history
    )


# ----------------------------
# Admin Dashboard route
# ----------------------------

@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    """Admin dashboard showing DevOps metrics: testing, security, CI/CD, performance"""
    try:
        # Wrap all calls in try-except to prevent Internal Server Errors
        test_coverage = get_test_coverage()
        test_results = get_test_results()
        security_metrics = get_security_metrics()
        security_score = get_security_score()
        critical_issues = get_critical_issues()
        action_items = get_action_items()
        system_health = get_system_health_summary()
        ci_cd_status = get_ci_cd_status()
        performance_metrics = get_performance_metrics()
        code_quality = get_code_quality_metrics()
        infrastructure = get_infrastructure_health()
        
        # Ensure all values are safe for template rendering
        if test_results is None:
            test_results = {
                'total': 0,
                'passed': 0,
                'failed': 0,
                'skipped': 0,
                'duration': 0,
                'exitcode': 0,
                'last_run': None
            }
        
        if code_quality is None:
            code_quality = {
                'total_files': 0,
                'total_lines': 0,
                'test_lines': 0,
                'code_to_test_ratio': 0
            }
        
        if system_health is None:
            system_health = {
                'overall_status': 'unknown',
                'overall_message': 'Unable to determine system health',
                'health_score': 0,
                'components': {}
            }
        
        return render_template(
            "admin/dashboard.html",
            test_coverage=test_coverage,
            test_results=test_results,
            security_metrics=security_metrics,
            security_score=security_score,
            critical_issues=critical_issues or [],
            action_items=action_items or [],
            system_health=system_health,
            ci_cd_status=ci_cd_status,
            performance_metrics=performance_metrics,
            code_quality=code_quality,
            infrastructure=infrastructure
        )
    except Exception as e:
        # Log error and return a safe error page
        app.logger.error(f"Error loading admin dashboard: {str(e)}", exc_info=True)
        flash(f"Error loading dashboard: {str(e)}", "error")
        return render_template(
            "admin/dashboard.html",
            test_coverage=None,
            test_results={'total': 0, 'passed': 0, 'failed': 0, 'skipped': 0, 'duration': 0, 'exitcode': 0, 'last_run': None},
            security_metrics={},
            security_score={'percentage': 0, 'grade': 'F'},
            critical_issues=[],
            action_items=[],
            system_health={'overall_status': 'error', 'overall_message': 'Error loading dashboard', 'health_score': 0, 'components': {}},
            ci_cd_status={},
            performance_metrics={},
            code_quality={'total_files': 0, 'total_lines': 0, 'test_lines': 0, 'code_to_test_ratio': 0},
            infrastructure={}
        )


if __name__ == "__main__":
    app.run()  # no debug=True here
