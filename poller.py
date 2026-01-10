# poller.py
import os, re, uuid, time, sys, fcntl, argparse
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Optional
from contextlib import contextmanager

from db import init_db, User, Alert, Delivery, Checkpoint
from emailer import send_email
from reddit_client import make_reddit
from logger import setup_logger
from praw.exceptions import RedditAPIException, PRAWException
from prawcore.exceptions import ResponseException, RequestException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text

logger = setup_logger("poller")
FETCH_LIMIT = int(os.getenv("FETCH_LIMIT", "100"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_DELAY = int(os.getenv("RETRY_DELAY", "5"))  # seconds
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "900"))  # 15 minutes default
LOCK_FILE_PATH = os.getenv("LOCK_FILE_PATH", "/tmp/poller.lock")


class PollerLock:
    """Distributed lock to prevent concurrent poller execution.

    Uses PostgreSQL advisory locks when available, falls back to file-based
    locking for SQLite (local development).
    """

    def __init__(self, session):
        self.session = session
        self.lock_file = None
        self.is_postgres = self._is_postgres()
        self.lock_acquired = False

    def _is_postgres(self) -> bool:
        """Check if we're using PostgreSQL."""
        try:
            dialect = self.session.bind.dialect.name
            return dialect == "postgresql"
        except Exception:
            return False

    def acquire(self) -> bool:
        """Attempt to acquire the lock. Returns True if successful."""
        if self.is_postgres:
            return self._acquire_postgres_lock()
        else:
            return self._acquire_file_lock()

    def release(self):
        """Release the lock."""
        if self.lock_acquired:
            if self.is_postgres:
                self._release_postgres_lock()
            else:
                self._release_file_lock()
            self.lock_acquired = False

    def _acquire_postgres_lock(self) -> bool:
        """Use PostgreSQL advisory lock (session-level, auto-releases on disconnect)."""
        try:
            # hashtext creates a consistent integer from string for advisory lock
            result = self.session.execute(
                text("SELECT pg_try_advisory_lock(hashtext('poller_main_lock'))")
            )
            acquired = result.scalar()
            if acquired:
                self.lock_acquired = True
                logger.debug("Acquired PostgreSQL advisory lock")
            return acquired
        except Exception as e:
            logger.error(f"Failed to acquire PostgreSQL lock: {e}")
            return False

    def _release_postgres_lock(self):
        """Release PostgreSQL advisory lock."""
        try:
            self.session.execute(
                text("SELECT pg_advisory_unlock(hashtext('poller_main_lock'))")
            )
            logger.debug("Released PostgreSQL advisory lock")
        except Exception as e:
            logger.error(f"Failed to release PostgreSQL lock: {e}")

    def _acquire_file_lock(self) -> bool:
        """Use file-based locking for SQLite/local development."""
        try:
            self.lock_file = open(LOCK_FILE_PATH, "w")
            fcntl.flock(self.lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.lock_acquired = True
            logger.debug(f"Acquired file lock: {LOCK_FILE_PATH}")
            return True
        except BlockingIOError:
            logger.warning("Another poller instance is running (file lock held)")
            if self.lock_file:
                self.lock_file.close()
                self.lock_file = None
            return False
        except Exception as e:
            logger.error(f"Failed to acquire file lock: {e}")
            return False

    def _release_file_lock(self):
        """Release file-based lock."""
        try:
            if self.lock_file:
                fcntl.flock(self.lock_file, fcntl.LOCK_UN)
                self.lock_file.close()
                self.lock_file = None
                logger.debug("Released file lock")
        except Exception as e:
            logger.error(f"Failed to release file lock: {e}")


@contextmanager
def poller_lock(session):
    """Context manager for acquiring and releasing the poller lock."""
    lock = PollerLock(session)
    try:
        if lock.acquire():
            yield True
        else:
            yield False
    finally:
        lock.release()

def _key_regex(kw: str):
    return re.compile(re.escape(kw), re.IGNORECASE)

def _local(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone()

def retry_on_error(func, *args, max_retries=MAX_RETRIES, delay=RETRY_DELAY, **kwargs):
    """Retry a function with exponential backoff on failure"""
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except (RedditAPIException, ResponseException, RequestException, PRAWException) as e:
            if attempt < max_retries - 1:
                wait_time = delay * (2 ** attempt)
                logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"All {max_retries} attempts failed: {e}")
                raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise

def run_once():
    """Main polling function that checks alerts and sends email notifications"""
    Session = init_db()
    session = Session()
    total_emails = 0

    try:
        # 1) Active alerts → unique (subreddit, keyword) pairs
        logger.info("Starting polling cycle")
        active = session.query(Alert).filter(Alert.is_active == True).all()
        pairs = {}
        for a in active:
            key = (a.subreddit.strip().lower().lstrip("r/"), a.keyword.strip())
            pairs[key] = pairs.get(key, []) + [a]

        if not pairs:
            logger.info("No active alerts found")
            return {"scanned_pairs": 0, "emails": 0}

        logger.info(f"Found {len(pairs)} unique (subreddit, keyword) pairs to monitor")

        # Initialize Reddit client with retry
        try:
            reddit = retry_on_error(make_reddit)
        except Exception as e:
            logger.error(f"Failed to initialize Reddit client: {e}")
            return {"scanned_pairs": 0, "emails": 0, "error": str(e)}

        for (subreddit, keyword), alerts in pairs.items():
            logger.info(f"Processing r/{subreddit} for keyword '{keyword}'")

            try:
                # 2) checkpoint
                chk = session.get(Checkpoint, {"subreddit": subreddit, "keyword": keyword})
                since = chk.last_seen_created_utc if chk else 0.0
                max_seen = since
                key_re = _key_regex(keyword)

                # 3) fetch newest posts with retry and process oldest→newest
                try:
                    posts = retry_on_error(
                        lambda: list(reddit.subreddit(subreddit).new(limit=FETCH_LIMIT))
                    )
                    posts.sort(key=lambda p: float(getattr(p, "created_utc", 0.0)))
                    logger.info(f"Fetched {len(posts)} posts from r/{subreddit}")
                except Exception as e:
                    logger.error(f"Failed to fetch posts from r/{subreddit}: {e}")
                    continue

                matched_posts = 0
                for post in posts:
                    created = float(getattr(post, "created_utc", 0.0))
                    if created <= since:
                        continue
                    if created > max_seen:
                        max_seen = created

                    title = getattr(post, "title", "") or ""
                    body = getattr(post, "selftext", "") or ""

                    if not (key_re.search(title) or key_re.search(body)):
                        continue

                    matched_posts += 1
                    logger.info(f"Match found: '{title[:100]}'")

                    # 4) email each subscribing user once
                    for a in alerts:
                        try:
                            # dedupe
                            exists = session.query(Delivery)\
                                .filter(Delivery.alert_id == a.id, Delivery.reddit_post_id == post.id)\
                                .first()
                            if exists:
                                logger.debug(f"Post {post.id} already delivered to alert {a.id}")
                                continue

                            # user email
                            user = session.query(User).filter(User.id == a.user_id).first()
                            if not user or not user.email:
                                logger.warning(f"User not found or no email for alert {a.id}")
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

                            # Send email with retry
                            try:
                                retry_on_error(send_email, user.email, subject, html)
                                total_emails += 1
                                logger.info(f"Email sent to {user.email} for post '{title[:50]}'")
                            except Exception as e:
                                logger.error(f"Failed to send email to {user.email}: {e}")
                                continue

                            # record delivery
                            session.add(Delivery(
                                id=str(uuid.uuid4()), alert_id=a.id,
                                reddit_post_id=post.id, delivered_at=datetime.utcnow()
                            ))
                            session.commit()

                        except SQLAlchemyError as e:
                            logger.error(f"Database error processing delivery: {e}")
                            session.rollback()
                            continue

                logger.info(f"Found {matched_posts} matching posts for r/{subreddit} + '{keyword}'")

                # 5) advance checkpoint for this pair
                try:
                    if not chk:
                        chk = Checkpoint(subreddit=subreddit, keyword=keyword, last_seen_created_utc=max_seen)
                        session.add(chk)
                        logger.debug(f"Created new checkpoint for r/{subreddit} + '{keyword}': {max_seen}")
                    else:
                        chk.last_seen_created_utc = max_seen
                        logger.debug(f"Updated checkpoint for r/{subreddit} + '{keyword}': {max_seen}")
                    session.commit()
                except SQLAlchemyError as e:
                    logger.error(f"Failed to update checkpoint: {e}")
                    session.rollback()

            except Exception as e:
                logger.error(f"Error processing r/{subreddit} + '{keyword}': {e}", exc_info=True)
                continue

        logger.info(f"Polling cycle complete: scanned {len(pairs)} pairs, sent {total_emails} emails")
        return {"scanned_pairs": len(pairs), "emails": total_emails}

    except Exception as e:
        logger.error(f"Critical error in polling cycle: {e}", exc_info=True)
        return {"scanned_pairs": 0, "emails": total_emails, "error": str(e)}
    finally:
        session.close()
        logger.debug("Database session closed")

def main():
    """Main entry point with argument parsing and locking."""
    parser = argparse.ArgumentParser(description="Reddit Alert Poller")
    parser.add_argument(
        "--loop",
        action="store_true",
        help=f"Run continuously with {POLL_INTERVAL}s interval (default: run once)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=POLL_INTERVAL,
        help=f"Polling interval in seconds when using --loop (default: {POLL_INTERVAL})"
    )
    parser.add_argument(
        "--skip-lock",
        action="store_true",
        help="Skip distributed lock (use only for debugging)"
    )
    args = parser.parse_args()

    # Initialize database to get session for locking
    Session = init_db()
    session = Session()

    try:
        if args.skip_lock:
            logger.warning("Running without distributed lock (--skip-lock)")
            if args.loop:
                _run_loop(args.interval)
            else:
                result = run_once()
                print(result)
            return

        # Acquire lock before running
        with poller_lock(session) as acquired:
            if not acquired:
                logger.warning("Could not acquire lock - another instance is running. Exiting.")
                sys.exit(0)

            logger.info("Lock acquired, starting poller")

            if args.loop:
                _run_loop(args.interval)
            else:
                result = run_once()
                print(result)

    finally:
        session.close()


def _run_loop(interval: int):
    """Run the poller continuously with the specified interval."""
    logger.info(f"Starting continuous polling with {interval}s interval")

    while True:
        try:
            result = run_once()
            logger.info(f"Poll complete: {result}")
        except Exception as e:
            logger.error(f"Error in polling loop: {e}", exc_info=True)

        logger.info(f"Sleeping for {interval} seconds...")
        time.sleep(interval)


if __name__ == "__main__":
    main()
