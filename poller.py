# poller.py
import os, re, uuid
from datetime import datetime, timezone

from db import init_db, User, Alert, Delivery, Checkpoint
from emailer import send_email
from reddit_client import make_reddit

FETCH_LIMIT = int(os.getenv("FETCH_LIMIT", "100"))

def _key_regex(kw: str):
    return re.compile(re.escape(kw), re.IGNORECASE)

def _local(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone()

def run_once():
    Session = init_db()
    session = Session()

    # 1) Active alerts → unique (subreddit, keyword) pairs
    active = session.query(Alert).filter(Alert.is_active == True).all()
    pairs = {}
    for a in active:
        key = (a.subreddit.strip().lower().lstrip("r/"), a.keyword.strip())
        pairs[key] = pairs.get(key, []) + [a]

    if not pairs:
        session.close()
        return {"scanned_pairs": 0, "emails": 0}

    reddit = make_reddit()
    total_emails = 0

    for (subreddit, keyword), alerts in pairs.items():
        # 2) checkpoint
        chk = session.get(Checkpoint, {"subreddit": subreddit, "keyword": keyword})
        since = chk.last_seen_created_utc if chk else 0.0
        max_seen = since
        key_re = _key_regex(keyword)

        # 3) fetch newest posts and process oldest→newest
        posts = list(reddit.subreddit(subreddit).new(limit=FETCH_LIMIT))
        posts.sort(key=lambda p: float(getattr(p, "created_utc", 0.0)))

        for post in posts:
            created = float(getattr(post, "created_utc", 0.0))
            if created <= since:
                continue
            if created > max_seen:
                max_seen = created

            title = getattr(post, "title", "") or ""
            print(title)
            body = getattr(post, "selftext", "") or ""
            if not (key_re.search(title) or key_re.search(body)):
                continue

            # 4) email each subscribing user once
            for a in alerts:
                # dedupe
                exists = session.query(Delivery)\
                    .filter(Delivery.alert_id == a.id, Delivery.reddit_post_id == post.id)\
                    .first()
                if exists:
                    continue

                # user email
                user = session.query(User).filter(User.id == a.user_id).first()
                if not user or not user.email:
                    continue

                permalink = f"https://www.reddit.com{post.permalink}"
                created_local = _local(created).strftime("%Y-%m-%d %H:%M:%S %Z")
                subject = f"[r/{subreddit}] '{keyword}' match: {title[:100]}"
                html = f"""
                  <div>
                    <h3>Match in r/{subreddit}</h3>
                    <p><b>Keyword:</b> {keyword}</p>
                    <p><b>Title:</b> {title}</p>
                    <p><b>When:</b> {created_local}</p>
                    <p><a href="{permalink}">{permalink}</a></p>
                    <hr/>
                    <pre style="white-space:pre-wrap">{body[:2000]}</pre>
                  </div>
                """
                send_email(user.email, subject, html)
                total_emails += 1

                # record delivery
                session.add(Delivery(
                    id=str(uuid.uuid4()), alert_id=a.id,
                    reddit_post_id=post.id, delivered_at=datetime.utcnow()
                ))
                session.commit()

        # 5) advance checkpoint for this pair
        if not chk:
            chk = Checkpoint(subreddit=subreddit, keyword=keyword, last_seen_created_utc=max_seen)
            session.add(chk)
        else:
            chk.last_seen_created_utc = max_seen
            print(max_seen)
        session.commit()

    session.close()
    return {"scanned_pairs": len(pairs), "emails": total_emails}

if __name__ == "__main__":
    result = run_once()
    print(result)
