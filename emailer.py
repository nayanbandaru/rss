# emailer.py
import os, ssl, re, smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
load_dotenv()


GMAIL_FROM = os.getenv("GMAIL_FROM")
GMAIL_PW = os.getenv("GMAIL_APP_PASSWORD")

def send_email(to_email: str, subject: str, html_body: str, text_body: str | None = None):
    if not (GMAIL_FROM and GMAIL_PW):
        raise RuntimeError("Gmail SMTP envs missing.")
    msg = MIMEMultipart("alternative")
    msg["From"] = GMAIL_FROM
    msg["To"] = to_email
    msg["Subject"] = subject
    if text_body is None:
        text_body = re.sub("<[^<]+?>", "", html_body)
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx) as server:
        server.login(GMAIL_FROM, GMAIL_PW)
        server.sendmail(GMAIL_FROM, [to_email], msg.as_string())
