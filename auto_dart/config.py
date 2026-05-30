import os
from dotenv import load_dotenv

load_dotenv()

DART_API_KEY = os.environ["DART_API_KEY"]
GMAIL_ADDRESS = os.environ["GMAIL_ADDRESS"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
NOTIFY_EMAIL = os.environ.get("NOTIFY_EMAIL", os.environ["GMAIL_ADDRESS"])
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
