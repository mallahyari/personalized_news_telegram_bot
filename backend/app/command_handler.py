from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.future import select
from app.config import NEWS_CATEGORIES
from app.database import User
from app.recommendation import generate_digest_for_user
import json
import logging

logger = logging.getLogger(__name__)

async def handle_command(message, session):
    """Handle specific bot commands"""
    command = message.text.split()[0].lower()
    user_id = message.from_user.id
    
    if command == "/start" or command == "/help":
        return await handle_help_command(user_id)
    elif command == "/categories":
        return await handle_categories_command(user_id)
    elif command == "/digest":
        return await handle_digest_command(user_id, session)
    elif command == "/time":
        return await handle_time_command(user_id)
    else:
        # Not a recognized command, process as regular message
        return None

async def handle_help_command(user_id):
    """Handle /help command"""
    help_text = (
        "🤖 *News Digest Bot Commands*\n\n"
        "/categories - Set your news preferences\n"
        "/digest - Get your news digest now\n"
        "/time - Set your daily digest time\n"
        "/help - Show this help message\n\n"
        "You can also just chat with me about news topics you're interested in!"
    )
    
    return {
        "chat_id": user_id,
        "text": help_text,
        "parse_mode": "Markdown"
    }

async def handle_categories_command(user_id):
    """Handle /categories command"""
    # Create keyboard with category options
    keyboard = []
    row = []
    
    for i, category in enumerate(NEWS_CATEGORIES):
        callback_data = json.dumps({"action": "select_category", "category": category})
        button = InlineKeyboardButton(category.title(), callback_data=callback_data)
        row.append(button)
        
        # 2 buttons per row
        if len(row) == 2 or i == len(NEWS_CATEGORIES) - 1:
            keyboard.append(row)
            row = []
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    return {
        "chat_id": user_id,
        "text": "Select news categories you're interested in:",
        "reply_markup": reply_markup
    }

async def handle_digest_command(user_id, session):
    """Handle /digest command"""
    # Get user
    result = await session.execute(
        select(User).where(User.telegram_id == user_id)
    )
    user = result.scalars().first()
    
    if not user:
        return {
            "chat_id": user_id,
            "text": "Sorry, I couldn't find your user profile. Please try again later."
        }
    
    # Generate digest
    digest = await generate_digest_for_user(user.id, session)
    markdown_digest = convert_markdown_to_markdown_v2(digest)
    
    if not digest:
        return {
            "chat_id": user_id,
            "text": "Sorry, I couldn't generate a digest at this time. Please try again later."
        }
    
    return {
        "chat_id": user_id,
        "text": markdown_digest,
        "parse_mode": "MarkdownV2"
    }

async def handle_time_command(user_id):
    """Handle /time command"""
    # Create keyboard with time options
    keyboard = []
    times = ["06:00", "08:00", "12:00", "18:00", "20:00", "22:00"]
    
    for i in range(0, len(times), 2):
        row = []
        for j in range(2):
            if i + j < len(times):
                time = times[i + j]
                callback_data = json.dumps({"action": "set_time", "time": time})
                button = InlineKeyboardButton(time, callback_data=callback_data)
                row.append(button)
        keyboard.append(row)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    return {
        "chat_id": user_id,
        "text": "Select your preferred daily digest time:",
        "reply_markup": reply_markup
    }
    
def convert_markdown_to_markdown_v2(markdown_text):
    """Convert regular Markdown to MarkdownV2, escaping necessary characters."""
    
    # List of characters that need to be escaped in MarkdownV2
    characters_to_escape = ['*', '_', '[', ']', '(', ')', '~', '#', '+', '-', '=', '{', '}', '.', '!', '`']
    
    # Escape each character
    for char in characters_to_escape:
        markdown_text = markdown_text.replace(char, f"\\{char}")
    
    return markdown_text