# Operational Dashboard Implementation Plan

**DevOps-focused dashboard reflecting operational aspects of the Blackjack web application**

---

## 📋 Table of Contents

1. [Overview - Operational Dashboard](#overview)
2. [Operational Metrics to Display](#operational-metrics)
3. [Data Sources Available](#data-sources)
4. [Implementation Plan](#implementation)
5. [Code Changes Required](#code-changes)
6. [Testing Plan](#testing)
7. [Deployment Readiness](#deployment)

---

## 🎯 Overview - Operational Dashboard {#overview}

### Purpose
Create an **operational dashboard** that reflects DevOps/system monitoring aspects:
- System health and availability
- User activity patterns
- Application performance metrics
- Database activity
- Service usage trends

### Target Audience
- **DevOps Engineers**
- **System Administrators**
- **Project Managers**
- **Development Team**

### Key Principle
**Focus on OPERATIONAL aspects**, not user game statistics. This is a system monitoring dashboard.

---

## 📊 Operational Metrics to Display {#operational-metrics}

### 1. System Health Metrics

#### User Metrics
- **Total Users**: Count of all registered users
- **Active Users (Last 24h)**: Users who logged in today
- **Active Users (Last 7 days)**: Users active in past week
- **New Users (Today)**: Users registered today
- **New Users (Last 7 days)**: Users registered in past week
- **New Users (Last 30 days)**: Users registered in past month

#### Application Activity Metrics
- **Total Games Played**: Count of all games (from HandHistory)
- **Games Today**: Games played today
- **Games (Last 24h)**: Games in last 24 hours
- **Games (Last 7 days)**: Games in past week
- **Games (Last 30 days)**: Games in past month
- **Peak Activity Hour**: Hour with most games
- **Average Games Per Day**: Average over last 30 days

#### Action/Event Metrics
- **Total Actions Logged**: Count of all ActionLog entries
- **Logins (Today)**: Login actions today
- **Logins (Last 7 days)**: Login actions in past week
- **Most Common Action**: Most frequent action type
- **Action Distribution**: Breakdown by action type (login, hit, stand, new_game, logout)

### 2. Time-Based Trends

#### Daily Activity
- **Games Per Day (Last 30 days)**: Daily game count trend
- **Users Per Day (Last 30 days)**: Daily new user registration trend
- **Logins Per Day (Last 30 days)**: Daily login activity trend

#### Hourly Patterns
- **Games By Hour**: Peak usage hours
- **Logins By Hour**: Login activity by hour of day
- **Activity Heatmap**: When users are most active

### 3. Performance Indicators

#### Game Performance
- **Win Rate (Overall)**: System-wide win rate
- **Average Games Per User**: Total games / total users
- **Most Active Users**: Top 10 users by game count
- **Game Completion Rate**: Games finished vs started

#### User Engagement
- **Average Session Duration**: Based on action_log timestamps
- **Returning Users**: Users with multiple logins
- **User Retention**: Users active in multiple days

### 4. System Status

#### Database Health
- **Database Connection Status**: ✅ Connected / ❌ Disconnected
- **Total Records**: Count across all tables
- **Database Size**: (if available)
- **Query Performance**: (if monitoring available)

#### Application Status
- **Uptime**: Application availability
- **Last Deployment**: (from CI/CD if available)
- **Current Environment**: Development / Production
- **Version Info**: (if available)

---

## 🗄️ Data Sources Available {#data-sources}

### Existing Database Tables

#### 1. `users` Table
**Operational Data Available**:
- Total user count
- User registration trends (created_at)
- User growth rate
- Active user identification

**Queries**:
```python
# Total users
User.query.count()

# New users today
User.query.filter(User.created_at >= today).count()

# New users last 7 days
User.query.filter(User.created_at >= seven_days_ago).count()
```

#### 2. `hand_history` Table
**Operational Data Available**:
- Total games played
- Games per day/hour
- Game activity trends
- System-wide win rate
- Peak activity times

**Queries**:
```python
# Total games
HandHistory.query.count()

# Games today
HandHistory.query.filter(HandHistory.created_at >= today).count()

# Games by hour
HandHistory.query.filter(HandHistory.created_at >= today)\
    .group_by(db.func.strftime('%H', HandHistory.created_at))\
    .all()
```

#### 3. `action_log` Table
**Operational Data Available**:
- User activity patterns
- Login frequency
- Action distribution
- User engagement metrics
- Session activity

**Queries**:
```python
# Total actions
ActionLog.query.count()

# Logins today
ActionLog.query.filter_by(action='login')\
    .filter(ActionLog.created_at >= today).count()

# Action distribution
ActionLog.query.with_entities(ActionLog.action, db.func.count(ActionLog.id))\
    .group_by(ActionLog.action).all()
```

---

## 💻 Implementation Plan {#implementation}

### Route
- **URL**: `/dashboard` (or `/admin/dashboard` for admin-only)
- **Access**: Requires login (`@login_required`)
- **Method**: GET

### Dashboard Sections

#### Section 1: System Overview Cards
```
┌─────────────┬─────────────┬─────────────┬─────────────┐
│ Total Users │ Active (24h)│ Games Today │ Logins Today│
└─────────────┴─────────────┴─────────────┴─────────────┘
```

#### Section 2: Activity Trends
- Games per day (last 30 days) - Table or simple chart
- User registrations per day (last 30 days)
- Activity by hour of day

#### Section 3: User Activity Metrics
- Most active users (top 10)
- Action distribution (pie chart or table)
- User engagement statistics

#### Section 4: System Status
- Database connection status
- Application health
- Recent activity summary

---

## 🔧 Step-by-Step Implementation {#step-by-step}

### Step 1: Add Operational Helper Functions

**Location**: `app.py` (after existing helper functions)

**Functions to Add**:

```python
# ----------------------------
# Operational Dashboard Helper Functions
# ----------------------------

def get_system_overview():
    """Get system-wide operational metrics"""
    from datetime import datetime, timedelta
    
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
    from datetime import datetime, timedelta
    from collections import defaultdict
    
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
    from datetime import datetime, timedelta
    from collections import defaultdict
    
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
```

### Step 2: Add Dashboard Route

**Location**: `app.py` (after game routes)

```python
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
```

### Step 3: Create Operational Dashboard Template

**Location**: `templates/dashboard.html` (new file)

**Template Structure**:

```jinja2
{% extends "base.html" %}

{% block content %}
  <h2>Operational Dashboard</h2>
  <p style="color: #666; margin-bottom: 30px;">System health and activity metrics</p>

  <!-- System Overview Cards -->
  <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0;">
    
    <!-- Total Users -->
    <div style="border: 1px solid #ddd; padding: 20px; border-radius: 8px; background: #f9f9f9; text-align: center;">
      <h3 style="margin: 0 0 10px 0; color: #666; font-size: 0.9em;">Total Users</h3>
      <p style="font-size: 2.5em; margin: 10px 0; font-weight: bold; color: #333;">{{ overview.total_users }}</p>
    </div>
    
    <!-- Active Users (24h) -->
    <div style="border: 1px solid #d4edda; padding: 20px; border-radius: 8px; background: #d4edda; text-align: center;">
      <h3 style="margin: 0 0 10px 0; color: #155724; font-size: 0.9em;">Active Users (24h)</h3>
      <p style="font-size: 2.5em; margin: 10px 0; font-weight: bold; color: #155724;">{{ overview.active_users_24h }}</p>
    </div>
    
    <!-- Games Today -->
    <div style="border: 1px solid #cce5ff; padding: 20px; border-radius: 8px; background: #e7f3ff; text-align: center;">
      <h3 style="margin: 0 0 10px 0; color: #004085; font-size: 0.9em;">Games Today</h3>
      <p style="font-size: 2.5em; margin: 10px 0; font-weight: bold; color: #004085;">{{ overview.games_today }}</p>
    </div>
    
    <!-- Total Games -->
    <div style="border: 1px solid #ddd; padding: 20px; border-radius: 8px; background: #f9f9f9; text-align: center;">
      <h3 style="margin: 0 0 10px 0; color: #666; font-size: 0.9em;">Total Games</h3>
      <p style="font-size: 2.5em; margin: 10px 0; font-weight: bold; color: #333;">{{ overview.total_games }}</p>
    </div>
    
    <!-- Logins Today -->
    <div style="border: 1px solid #fff3cd; padding: 20px; border-radius: 8px; background: #fff3cd; text-align: center;">
      <h3 style="margin: 0 0 10px 0; color: #856404; font-size: 0.9em;">Logins Today</h3>
      <p style="font-size: 2.5em; margin: 10px 0; font-weight: bold; color: #856404;">{{ overview.logins_today }}</p>
    </div>
    
    <!-- New Users (7d) -->
    <div style="border: 1px solid #d1ecf1; padding: 20px; border-radius: 8px; background: #d1ecf1; text-align: center;">
      <h3 style="margin: 0 0 10px 0; color: #0c5460; font-size: 0.9em;">New Users (7d)</h3>
      <p style="font-size: 2.5em; margin: 10px 0; font-weight: bold; color: #0c5460;">{{ overview.new_users_7d }}</p>
    </div>
    
  </div>

  <!-- System Health Status -->
  <div style="margin: 30px 0; padding: 20px; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #28a745;">
    <h3 style="margin: 0 0 15px 0;">System Health</h3>
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
      <div>
        <strong>Database Status:</strong>
        <span style="color: {% if system_health.database_status == 'connected' %}#28a745{% else %}#dc3545{% endif %};">
          {% if system_health.database_status == 'connected' %}✅ Connected{% else %}❌ Disconnected{% endif %}
        </span>
      </div>
      <div>
        <strong>Total Records:</strong>
        {{ system_health.total_records.users }} users,
        {{ system_health.total_records.games }} games,
        {{ system_health.total_records.actions }} actions
      </div>
      <div>
        <strong>Avg Games/User:</strong> {{ system_health.avg_games_per_user }}
      </div>
      <div>
        <strong>Overall Win Rate:</strong> {{ system_health.overall_win_rate }}%
      </div>
    </div>
  </div>

  <!-- Daily Activity Trends -->
  <div style="margin: 30px 0;">
    <h3>Daily Activity (Last 30 Days)</h3>
    <div style="overflow-x: auto;">
      <table style="width: 100%; border-collapse: collapse; margin-top: 10px; background: white;">
        <thead>
          <tr style="background: #f8f9fa;">
            <th style="padding: 12px; text-align: left; border-bottom: 2px solid #dee2e6;">Date</th>
            <th style="padding: 12px; text-align: center; border-bottom: 2px solid #dee2e6;">Games</th>
            <th style="padding: 12px; text-align: center; border-bottom: 2px solid #dee2e6;">New Users</th>
            <th style="padding: 12px; text-align: center; border-bottom: 2px solid #dee2e6;">Logins</th>
          </tr>
        </thead>
        <tbody>
          {% for day in daily_activity[-7:] %}
          <tr style="border-bottom: 1px solid #dee2e6;">
            <td style="padding: 10px;">{{ day.date.strftime('%Y-%m-%d') }}</td>
            <td style="padding: 10px; text-align: center;">{{ day.games }}</td>
            <td style="padding: 10px; text-align: center;">{{ day.new_users }}</td>
            <td style="padding: 10px; text-align: center;">{{ day.logins }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </div>

  <!-- Action Distribution -->
  <div style="margin: 30px 0;">
    <h3>Action Distribution</h3>
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-top: 15px;">
      {% for action, count in action_distribution.items() %}
      <div style="border: 1px solid #ddd; padding: 15px; border-radius: 8px; text-align: center;">
        <div style="font-size: 0.9em; color: #666; margin-bottom: 5px;">{{ action|title }}</div>
        <div style="font-size: 1.8em; font-weight: bold; color: #333;">{{ count }}</div>
      </div>
      {% endfor %}
    </div>
  </div>

  <!-- Most Active Users -->
  <div style="margin: 30px 0;">
    <h3>Most Active Users (Top 10)</h3>
    <div style="overflow-x: auto;">
      <table style="width: 100%; border-collapse: collapse; margin-top: 10px; background: white;">
        <thead>
          <tr style="background: #f8f9fa;">
            <th style="padding: 12px; text-align: left; border-bottom: 2px solid #dee2e6;">Rank</th>
            <th style="padding: 12px; text-align: left; border-bottom: 2px solid #dee2e6;">Username</th>
            <th style="padding: 12px; text-align: center; border-bottom: 2px solid #dee2e6;">Games Played</th>
          </tr>
        </thead>
        <tbody>
          {% for user in active_users %}
          <tr style="border-bottom: 1px solid #dee2e6;">
            <td style="padding: 10px;">{{ loop.index }}</td>
            <td style="padding: 10px;">{{ user.username }}</td>
            <td style="padding: 10px; text-align: center;">{{ user.game_count }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </div>

  <!-- Hourly Activity Pattern -->
  <div style="margin: 30px 0;">
    <h3>Activity by Hour (Last 7 Days)</h3>
    <div style="overflow-x: auto;">
      <table style="width: 100%; border-collapse: collapse; margin-top: 10px; background: white;">
        <thead>
          <tr style="background: #f8f9fa;">
            <th style="padding: 12px; text-align: left; border-bottom: 2px solid #dee2e6;">Hour</th>
            <th style="padding: 12px; text-align: center; border-bottom: 2px solid #dee2e6;">Games</th>
            <th style="padding: 12px; text-align: center; border-bottom: 2px solid #dee2e6;">Logins</th>
          </tr>
        </thead>
        <tbody>
          {% for hour_data in hourly_activity %}
          <tr style="border-bottom: 1px solid #dee2e6;">
            <td style="padding: 10px;">{{ hour_data.hour }}:00</td>
            <td style="padding: 10px; text-align: center;">{{ hour_data.games }}</td>
            <td style="padding: 10px; text-align: center;">{{ hour_data.logins }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </div>

  <!-- Quick Actions -->
  <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #dee2e6;">
    <a href="{{ url_for('index') }}" class="button">← Back to Game</a>
  </div>
{% endblock %}
```

### Step 4: Add Navigation Link

**Location**: `templates/base.html`

Add dashboard link to navigation:
```html
<div>
  {% if session.user %}
    Logged in as {{ session.user }} |
    <a href="{{ url_for('index') }}" class="button">Game</a>
    <a href="{{ url_for('dashboard') }}" class="button">Dashboard</a>
    <a href="{{ url_for('logout') }}" class="button">Logout</a>
  {% endif %}
</div>
```

---

## 📝 Code Changes Summary {#code-changes}

### Files to Modify

1. **app.py**:
   - Add 5 helper functions (~150 lines)
   - Add 1 dashboard route (~15 lines)
   - **Total**: ~165 lines

2. **templates/dashboard.html**:
   - Create new file (~250 lines)

3. **templates/base.html**:
   - Add 1 navigation link (~1 line)

**Total Changes**: ~416 lines of code

### No Database Changes Required

✅ **No migrations needed** - uses existing tables:
- `users` table
- `hand_history` table  
- `action_log` table

---

## 🧪 Testing Plan {#testing}

### Required Tests

**Add to `tests/test_routes.py`**:

```python
def test_dashboard_requires_login(client):
    """Dashboard should redirect if not authenticated"""
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.location

def test_dashboard_displays_operational_metrics(client, db_session):
    """Dashboard should show operational metrics"""
    username = create_and_login_user(client, db_session)
    
    # Create some data
    user = User.query.filter_by(username=username).first()
    HandHistory(user_id=user.id, result='win')
    ActionLog(user_id=user.id, action='login')
    db_session.commit()
    
    response = client.get("/dashboard", follow_redirects=True)
    assert response.status_code == 200
    assert b"Operational Dashboard" in response.data
    assert b"Total Users" in response.data
    assert b"Games Today" in response.data
    assert b"System Health" in response.data
```

---

## ✅ Compatibility Verification {#compatibility}

### Database Compatibility

**SQLite (Local Development)**:
- ✅ All queries use SQLAlchemy ORM (database-agnostic)
- ✅ Date comparisons work with `datetime` objects
- ✅ `filter()` with multiple conditions works correctly
- ✅ `group_by()` and `order_by()` work correctly
- ✅ `with_entities()` and `func.count()` work correctly
- ✅ Active users count uses Python set (works on both databases)

**PostgreSQL (Production)**:
- ✅ All queries use SQLAlchemy ORM (database-agnostic)
- ✅ DateTime columns map correctly
- ✅ All aggregation functions work
- ✅ Foreign key relationships work

### Code Structure Compatibility

**Existing Patterns Used**:
- ✅ `User.query.filter_by()` - matches existing code
- ✅ `HandHistory.query.filter_by()` - matches existing code
- ✅ `ActionLog.query.filter()` - matches existing code
- ✅ `datetime.utcnow()` - matches existing code
- ✅ `@login_required` decorator - matches existing code
- ✅ `render_template()` - matches existing code

**Template Compatibility**:
- ✅ Extends `base.html` - matches existing templates
- ✅ Uses inline CSS - matches existing style
- ✅ Uses Jinja2 syntax - matches existing templates
- ✅ No JavaScript required - matches existing approach

### Import Compatibility

**Required Imports** (all standard):
- ✅ `from datetime import datetime, timedelta` - standard library
- ✅ `from collections import defaultdict` - standard library
- ✅ `from sqlalchemy import func` - already used in SQLAlchemy
- ✅ All other imports already in `app.py`

### No Breaking Changes

- ✅ No existing routes modified
- ✅ No existing functions modified
- ✅ No database schema changes
- ✅ No new dependencies required
- ✅ All existing tests will continue to pass

---

## 🚀 Deployment Readiness {#deployment}

### ✅ Deployment Ready

**Yes, the operational dashboard will be deployment ready** because:

1. **No Database Changes**: Uses existing tables
2. **No Breaking Changes**: All changes are additive
3. **Database Compatible**: Works with SQLite and PostgreSQL
4. **Follows Patterns**: Matches existing code style
5. **Secure**: Uses existing authentication
6. **Testable**: Easy to add tests

### Requirements

- [ ] Add tests to maintain 75% coverage
- [ ] Manual testing completed
- [ ] All existing tests pass
- [ ] Code review done

**See `DEPLOYMENT_READINESS.md` for complete checklist.**

---

## 🎯 Summary

### What We're Building

An **operational/DevOps dashboard** that shows:
- System health metrics
- User activity patterns
- Application performance
- Database activity
- Time-based trends
- Service usage statistics

### Key Operational Aspects

1. **System Health**: Database status, record counts
2. **User Activity**: Active users, new registrations, engagement
3. **Application Activity**: Games played, logins, actions
4. **Time Trends**: Daily/hourly activity patterns
5. **Performance**: Average metrics, win rates, user engagement

### Implementation Effort

- **Time Estimate**: 4-6 hours
- **Code Changes**: ~416 lines
- **Files Modified**: 3 files (1 new, 2 modified)
- **Database Changes**: None required
- **Breaking Changes**: None

---

**This operational dashboard reflects DevOps/system monitoring aspects as required by the professor.**
