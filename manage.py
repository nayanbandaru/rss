# manage.py
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
    a = Alert(id=str(uuid.uuid4()), user_id=user_id, subreddit=subreddit, keyword=keyword, is_active=True)
    s.add(a); s.commit()
    print(f"Created alert {a.id} for {user_id}: r/{subreddit} -> '{keyword}'")
    s.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:\n  python manage.py add-user you@example.com\n  python manage.py add-alert you@example.com Watchexchange SBCJ031")
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "add-user":
        add_user(sys.argv[2])
    elif cmd == "add-alert":
        add_alert(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        print("Unknown command.")
