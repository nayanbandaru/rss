# reddit_client.py
import os, praw
from dotenv import load_dotenv
load_dotenv()


def make_reddit():
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    user_agent = os.getenv("REDDIT_USER_AGENT", "watcher-backend/0.1")
    username = os.getenv("REDDIT_USERNAME")
    password = os.getenv("REDDIT_PASSWORD")

    if not (client_id and client_secret and user_agent):
        raise RuntimeError("Reddit credentials missing.")

    if username and password:
        return praw.Reddit(
            client_id=client_id, client_secret=client_secret, user_agent=user_agent,
            username=username, password=password, ratelimit_seconds=5
        )
    return praw.Reddit(
        client_id=client_id, client_secret=client_secret, user_agent=user_agent, ratelimit_seconds=5
    )
