import logging
from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from app.config import GEMINI_API_KEY, LLM_MODEL
from app.database import Conversation, User, Article, user_interactions
from litellm import acompletion
import json

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are a helpful and knowledgeable news assistant for a media company.
Your job is to have natural conversations about news and current events,
help users discover content they might be interested in, and provide
summaries and insights about news articles.

Keep your responses conversational and engaging. When appropriate, ask follow-up
questions to better understand the user's interests. If the user asks about specific
news topics, try to respond with relevant information and offer to include similar
topics in their daily digest.

The user's current news preferences are: {preferences}

Recent articles discussed with this user: {recent_articles}

Respond in markdown format.
"""

async def get_conversation_history(session, user_id, limit=5):
    """Fetch recent conversation history for context"""
    result = await session.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.timestamp.desc())
        .limit(limit)
    )
    conversations = result.scalars().all()
    # Convert to list of messages for context
    history = []
    for conv in reversed(conversations):
        history.append({"role": "user", "content": conv.message})
        history.append({"role": "assistant", "content": conv.response})
    return history

async def get_user_preferences(user, session):
    """Get user preferences as a formatted string"""
    try:
        result = await session.execute(
        select(User)
        .options(joinedload(User.categories))  # Eagerly load categories
        .where(User.id == user.id)
        )
        user = result.scalars().first()
        logger.info(f"User categories======>: {user.categories}")
        if not user.categories:
            return "No specific preferences set yet."
        return ", ".join([cat.name for cat in user.categories])
    except Exception as e:
        logger.info(f"Error getting user preferences: {e}")
        return "Error fetching preferences."

async def get_recent_articles(session, user_id, limit=3):
    """Get recently discussed articles based on user interactions."""
    try:
        # Query user interactions, join with articles, and filter by user_id
        result = await session.execute(
            select(Article)
            .join(user_interactions)
            .where(user_interactions.c.user_id == user_id)
            .order_by(user_interactions.c.timestamp.desc())  # Order by most recent interaction
            .limit(limit)
        )
        
        # Fetch the articles
        articles = result.scalars().all()
        
        if not articles:
            return "No recent articles discussed."
        
        # Return the article titles as a formatted string
        return "\n".join([article.title for article in articles])
    
    except Exception as e:
        logger.error(f"Error fetching recent articles for user {user_id}: {e}")
        return "Error fetching recent articles."

async def process_message_with_llm(message, user, session):
    """Process a user message with the LLM and generate a response"""
    # logger.info(f"------->Processing message with LLM: {message}")
    # Get user preferences
    preferences = await get_user_preferences(user, session)
    
    logger.info(f"++++++++User preferences: {preferences}")
    
    # Get recent articles
    recent_articles = await get_recent_articles(session, user.id)
    
    # Get conversation history
    history = await get_conversation_history(session, user.id)
    
    # Create system prompt with user context
    system_message = SYSTEM_PROMPT.format(
        preferences=preferences,
        recent_articles=recent_articles
    )
    
    logger.info(f"+++++++++++++++++++++++++++++========>System message: {system_message}")
    
    # Build the messages for the LLM
    messages = [
        {"role": "system", "content": system_message}
    ]
    
    # Add conversation history if available
    if history:
        messages.extend(history)
    
    # Add the current message
    messages.append({"role": "user", "content": message})
    
    try:
        # Call the LLM API
        response = await acompletion(
            model=LLM_MODEL,
            messages=messages,
            max_tokens=500,
            temperature=0.7
        )
        
        response_text = response.choices[0].message.content
        
        return response_text
    except Exception as e:
        logger.error(f"Error calling LLM API: {e}")
        return "Sorry, I'm having trouble processing your request right now. Please try again later."

async def save_conversation(session, user_id, message, response):
    """Save the conversation to the database"""
    conversation = Conversation(
        user_id=user_id,
        message=message,
        response=response,
        timestamp=datetime.utcnow()
    )
    session.add(conversation)
    await session.commit()
    return conversation

async def analyze_message_for_preferences(message, session):
    """Analyze user message to extract implicit preferences"""
    # This would be a more advanced feature, using the LLM to extract 
    # interest signals from natural conversation
    
    # Example implementation:
    try:
        response = await acompletion(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "Extract news categories that the user might be interested in based on their message. Respond with a JSON array of category names from this list: politics, business, technology, science, health, entertainment, sports. If no categories are mentioned or implied, return an empty array."},
                {"role": "user", "content": message}
            ],
            max_tokens=100,
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        logger.info(f"LLM response category extraction=====>: {content}")
        try:
            categories = json.loads(content)
            return categories if isinstance(categories, list) else []
        except:
            logger.error(f"Failed to parse categories from LLM response: {content}")
            return []
    except Exception as e:
        logger.error(f"Error analyzing message for preferences: {e}")
        return []