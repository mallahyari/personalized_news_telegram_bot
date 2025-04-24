import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Telegram settings
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Database settings
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///news_digest.db")

# LLM settings
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

# News settings
NEWS_SOURCES= ["https://www.cnn.com"]
NEWS_UPDATE_INTERVAL = int(os.getenv("NEWS_UPDATE_INTERVAL", 60))  # minutes
NEWS_CATEGORIES = ["politics", "business", "technology", "science", "health", "entertainment", "sports"]
# NEWS_CATEGORIES = ["politics", "business", "technology", "science", "health", "entertainment", "sports"]

# Digest settings
DEFAULT_DIGEST_TIME = "08:00"  # Default time for daily digest (24-hour format)
ARTICLES_PER_DIGEST = int(os.getenv("ARTICLES_PER_DIGEST", 5))