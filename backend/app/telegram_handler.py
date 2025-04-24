from telegram import Bot, Update
from telegram.constants import ParseMode
from app.config import TELEGRAM_TOKEN, NEWS_CATEGORIES
from app.database import Category, User, get_user_by_telegram_id, create_user, user_interactions
from datetime import datetime
from app.conversation import process_message_with_llm, save_conversation
from app.command_handler import convert_markdown_to_markdown_v2, handle_command
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
import markdown
import logging
import json
import re


logger = logging.getLogger(__name__)

bot = Bot(token=TELEGRAM_TOKEN)


async def process_telegram_update(update_data, session):
    # Convert the update data to an Update object
    update = Update.de_json(data=update_data, bot=bot)
    
    # Process different types of updates
    if update.message:
        await handle_message(update.message, session)
    elif update.callback_query:
        await handle_callback_query(update.callback_query, session)

async def handle_message(message, session):
    logger.info(f"Received message from {message.from_user.username}: {message}")
    user_id = message.from_user.id
    text = message.text
    
    # Get or create user
    user = await get_user_by_telegram_id(session, user_id)
    if not user:
        user = await create_user(
            session,
            user_id,
            message.from_user.first_name,
            message.from_user.last_name,
            message.from_user.username
        )
        # Send welcome message
        await send_welcome_message(user_id)
        return
    
    # Check if this is a command
    if text and text.startswith('/'):
        command_response = await handle_command(message, session)
        if command_response:
            await bot.send_message(**command_response)
            return
    
    # Process message with LLM if not a command or command not recognized
    if text:
        response_text = await process_message_with_llm(text, user, session)
        
        # Save conversation
        await save_conversation(session, user.id, text, response_text)
        markdown_v2_text = convert_markdown_to_markdown_v2(response_text)
        
        # Send response
        await bot.send_message(
            chat_id=user_id,
            text=markdown_v2_text,
            parse_mode=ParseMode.MARKDOWN_V2
        )

async def handle_callback_query(callback_query, session):
    user_id = callback_query.from_user.id
    data = callback_query.data
    
    # Parse callback data
    callback_data = json.loads(data)
    action = callback_data.get("action")
    
    # Get user
    user = await get_user_by_telegram_id(session, user_id)
    if not user:
        await callback_query.answer("User not found. Please start a new conversation.")
        return
    
    # Handle different callback actions
    if action == "select_category":
        category = callback_data.get("category")
        # Update user preferences
        await update_user_category(session, user.id, category)
        await bot.answer_callback_query(
            callback_query.id,
            text=f"Added {category} to your interests!"
        )
    elif action == "feedback":
        article_id = callback_data.get("article_id")
        feedback_type = callback_data.get("type")  # "like" or "dislike"
        # Save user feedback
        await save_article_feedback(session, user.id, article_id, feedback_type)
        await bot.answer_callback_query(
            callback_query.id,
            text="Thanks for your feedback!"
        )
    elif action == "set_time":
        time = callback_data.get("time")
        # Update digest time
        await update_digest_time(session, user.id, time)
        await bot.answer_callback_query(
            callback_query.id,
            text=f"Digest time set to {time}!"
        )

async def send_welcome_message(user_id):
    welcome_text = (
        "👋 *Welcome to the News Digest Bot!*\n\n"
        "I'm your personal news assistant. I can deliver daily news digests tailored to your interests "
        "and have conversations about current events.\n\n"
        "Let me know what topics you're interested in, or just chat with me about the news. "
        "You can also use these commands:\n\n"
        "/categories - Set your news preferences\n"
        "/digest - Get your news digest now\n"
        "/time - Set your daily digest time\n"
        "/help - Show all available commands"
    )
    
    await bot.send_message(
        chat_id=user_id,
        text=welcome_text,
        parse_mode=ParseMode.MARKDOWN
    )

async def update_user_category(session, user_id, category):
    """Update user category preferences"""
    # Get user with categories preloaded
    result = await session.execute(
        select(User).where(User.id == user_id).options(selectinload(User.categories))
    )
    user = result.scalars().first()
    
    # logger.info(f"User categories======>: {user.__dict__}")
    
    if not user:
        return False
    
    # Get category
    result = await session.execute(select(Category).where(Category.name == category))
    category_obj = result.scalars().first()
    # logger.info(f"Category======>: {category_obj.__dict__}")
    
    if not category_obj:
        # Create category if it doesn't exist
        category_obj = Category(name=category)
        session.add(category_obj)
        await session.commit() 
    
    # Add category to user if not already present
    if category_obj not in user.categories:
        user.categories.append(category_obj)
        await session.commit()
    
    return True

async def save_article_feedback(session, user_id, article_id, feedback_type):
    """Save user feedback on an article"""
    # Insert into user_interactions
    stmt = user_interactions.insert().values(
        user_id=user_id,
        article_id=article_id,
        interaction_type=feedback_type,
        timestamp=datetime.utcnow()
    )
    await session.execute(stmt)
    await session.commit()
    return True

async def update_digest_time(session, user_id, time):
    """Update user's preferred digest time"""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    
    if not user:
        return False
    
    user.digest_time = time
    await session.commit()
    return True


def markdown_to_html(md_text):
    """Convert Markdown to HTML"""
    return markdown.markdown(md_text)


