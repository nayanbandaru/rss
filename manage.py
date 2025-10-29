import sys, uuid
from email_validator import validate_email, EmailNotValidError
from db import init_db, User, Alert

def add_user(email: str):
    Session = init_db()
    s = Session()
    try:
        validate_email(email)
    except EmailNotValidError as e:
        raise SystemExit(f"Invalid email: {e}")
    user = s.query(User).filter(User.email == email).first()
    if user:
        print(f"User exists: {user.id} {user.email}")
        s.close()
        return user.id
    user = User(id=email, email=email)  # use email as id for MVP
    s.add(user); s.commit()
    print(f"Created user: {user.id}")
    s.close()
    return user.id

def add_alert(user_id: str, subreddit: str, keyword: str):
    subreddit = subreddit.replace("r/", "").strip()
    keyword = keyword.strip()
    Session = init_db()
    s = Session()
    
    # Check if user exists
    user = s.query(User).filter(User.id == user_id).first()
    if not user:
        print(f"Error: User {user_id} not found. Create user first with: add-user {user_id}")
        s.close()
        return
    
    # Check for duplicate
    existing = s.query(Alert).filter(
        Alert.user_id == user_id,
        Alert.subreddit == subreddit,
        Alert.keyword == keyword
    ).first()
    
    if existing:
        print(f"Alert already exists: {existing.id}")
        s.close()
        return
    
    a = Alert(id=str(uuid.uuid4()), user_id=user_id, subreddit=subreddit, keyword=keyword, is_active=True)
    s.add(a); s.commit()
    print(f"Created alert {a.id} for {user_id}: r/{subreddit} -> '{keyword}'")
    s.close()

def list_users():
    """List all users with alert counts"""
    Session = init_db()
    s = Session()
    
    users = s.query(User).all()
    print(f"\nAll users ({len(users)} total):")
    
    if not users:
        print("  (none)")
    else:
        for user in users:
            # Count alerts for this user
            alert_count = s.query(Alert).filter(Alert.user_id == user.id).count()
            active_count = s.query(Alert).filter(
                Alert.user_id == user.id, 
                Alert.is_active == True
            ).count()
            print(f"  {user.email} | {active_count}/{alert_count} alerts active")
    
    s.close()

def list_alerts(user_id: str = None):
    """List all alerts, optionally filtered by user"""
    Session = init_db()
    s = Session()
    
    if user_id:
        alerts = s.query(Alert).filter(Alert.user_id == user_id).all()
        print(f"\nAlerts for {user_id}:")
    else:
        alerts = s.query(Alert).all()
        print(f"\nAll alerts:")
    
    if not alerts:
        print("  (none)")
    else:
        for a in alerts:
            status = "✓ active" if a.is_active else "✗ inactive"
            print(f"  [{a.id}] {a.user_id} | r/{a.subreddit} | '{a.keyword}' | {status}")
    
    s.close()

def delete_alert(alert_id: str):
    """Delete an alert by ID"""
    Session = init_db()
    s = Session()
    
    alert = s.query(Alert).filter(Alert.id == alert_id).first()
    
    if not alert:
        print(f"Error: Alert {alert_id} not found")
        s.close()
        return
    
    print(f"Deleting alert: {alert.user_id} | r/{alert.subreddit} | '{alert.keyword}'")
    s.delete(alert)
    s.commit()
    print(f"Alert {alert_id} deleted successfully")
    s.close()

def delete_user_alerts(user_id: str):
    """Delete all alerts for a specific user"""
    Session = init_db()
    s = Session()
    
    alerts = s.query(Alert).filter(Alert.user_id == user_id).all()
    
    if not alerts:
        print(f"No alerts found for user {user_id}")
        s.close()
        return
    
    print(f"Found {len(alerts)} alerts for {user_id}:")
    for a in alerts:
        print(f"  - r/{a.subreddit} | '{a.keyword}'")
    
    confirm = input(f"\nDelete all {len(alerts)} alerts? (yes/no): ")
    if confirm.lower() in ['yes', 'y']:
        for alert in alerts:
            s.delete(alert)
        s.commit()
        print(f"Deleted {len(alerts)} alerts for {user_id}")
    else:
        print("Cancelled")
    
    s.close()

def toggle_alert(alert_id: str):
    """Toggle alert active status"""
    Session = init_db()
    s = Session()
    
    alert = s.query(Alert).filter(Alert.id == alert_id).first()
    
    if not alert:
        print(f"Error: Alert {alert_id} not found")
        s.close()
        return
    
    alert.is_active = not alert.is_active
    s.commit()
    
    status = "activated" if alert.is_active else "deactivated"
    print(f"Alert {status}: {alert.user_id} | r/{alert.subreddit} | '{alert.keyword}'")
    s.close()

def print_usage():
    print("""
Usage:
  python manage.py add-user <email>
  python manage.py add-alert <email> <subreddit> "<keyword>"
  python manage.py list-users
  python manage.py list-alerts [email]
  python manage.py delete-alert <alert_id>
  python manage.py delete-user-alerts <email>
  python manage.py toggle-alert <alert_id>

Examples:
  python manage.py add-user alice@example.com
  python manage.py add-alert alice@example.com watchexchange "Seiko SARB"
  python manage.py add-alert alice@example.com mechmarket "keycaps"
  python manage.py list-users
  python manage.py list-alerts
  python manage.py list-alerts alice@example.com
  python manage.py delete-alert abc-123-def
  python manage.py delete-user-alerts alice@example.com
  python manage.py toggle-alert abc-123-def

Notes:
  - Use quotes around multi-word keywords: "Brandy Melville"
  - Subreddit can be "watchexchange" or "r/watchexchange"
  - Alert IDs are shown in list-alerts output
""")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "add-user":
        if len(sys.argv) < 3:
            print("Error: Missing email")
            print('Usage: python manage.py add-user <email>')
            sys.exit(1)
        add_user(sys.argv[2])
    
    elif cmd == "add-alert":
        if len(sys.argv) < 5:
            print("Error: Missing arguments")
            print('Usage: python manage.py add-alert <email> <subreddit> "<keyword>"')
            print('Example: python manage.py add-alert alice@example.com watchexchange "Seiko SARB"')
            sys.exit(1)
        # Join remaining args as keyword (supports multi-word keywords)
        keyword = " ".join(sys.argv[4:])
        add_alert(sys.argv[2], sys.argv[3], keyword)
    
    elif cmd == "list-users":
        list_users()
    
    elif cmd == "list-alerts":
        user_id = sys.argv[2] if len(sys.argv) > 2 else None
        list_alerts(user_id)
    
    elif cmd == "delete-alert":
        if len(sys.argv) < 3:
            print("Error: Missing alert ID")
            print('Usage: python manage.py delete-alert <alert_id>')
            print('Tip: Use "list-alerts" to see alert IDs')
            sys.exit(1)
        delete_alert(sys.argv[2])
    
    elif cmd == "delete-user-alerts":
        if len(sys.argv) < 3:
            print("Error: Missing user email")
            print('Usage: python manage.py delete-user-alerts <email>')
            sys.exit(1)
        delete_user_alerts(sys.argv[2])
    
    elif cmd == "toggle-alert":
        if len(sys.argv) < 3:
            print("Error: Missing alert ID")
            print('Usage: python manage.py toggle-alert <alert_id>')
            sys.exit(1)
        toggle_alert(sys.argv[2])
    
    else:
        print(f"Error: Unknown command '{cmd}'")
        print_usage()
        sys.exit(1)