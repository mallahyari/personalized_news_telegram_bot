
from app.config import GEMINI_API_KEY, LLM_MODEL, ARTICLES_PER_DIGEST
from app.database import User, Article, Conversation, user_interactions
from app.news_service import get_articles_for_digest
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from litellm import acompletion
from datetime import datetime, timedelta
import logging
import openai
import json

logger = logging.getLogger(__name__)

# Configure OpenAI
openai.api_key = GEMINI_API_KEY

async def generate_digest_for_user(user_id, session):
    """Generate a personalized news digest for a user"""
    # Get user
    result = await session.execute(
        select(User).where(User.id == user_id).options(selectinload(User.categories))
    )
    user = result.scalars().first()
    
    if not user:
        logger.error(f"User not found: {user_id}")
        return None
    
    # Get user categories
    user_categories = user.categories
    
    logger.info(f"%%%%%%%%%%%%User {user_id} has categories: {[cat.name for cat in user_categories]}")
    
    # If user has no categories, use default ones
    if not user_categories:
        logger.info(f"User {user_id} has no categories, using defaults")
        return await generate_general_digest(session)
    
    # Get recent articles for user's categories
    articles = await get_articles_for_digest(session, user_categories)
    
    
    # Get user's conversation history for context
    conversations = await get_recent_conversations(user_id, session, limit=5)
    formatted_conversation = "\n".join(
        f"User: {conv.message}\nAssistant: {conv.response}" for conv in conversations
    )
    
    # Generate personalized digest using LLM
    digest = await generate_personalized_digest_with_llm(user, articles, formatted_conversation)
    
    return digest

async def get_recent_conversations(user_id, session, limit=5):
    """Get recent conversations for a user"""
    result = await session.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.timestamp.desc())
        .limit(limit)
    )
    return result.scalars().all()

async def generate_general_digest(session):
    """Generate a general digest for users with no preferences"""
    # Get recent articles from various categories
    articles = []
    for category in ["politics", "technology", "health", "entertainment"]:
        result = await session.execute(
            select(Article)
            .join(Article.category)
            .where(Category.name == category)
            .order_by(Article.published_at.desc())
            .limit(2)
        )
        articles.extend(result.scalars().all())
    
    # Sort by publication date
    articles.sort(key=lambda x: x.published_at, reverse=True)
    
    # Generate digest
    return await format_digest(articles, personalized=False)

async def generate_personalized_digest_with_llm(user, articles, conversation):
    """Use LLM to generate a personalized news digest"""
    # Prepare article data
    article_data = []
    for article in articles:
        article_data.append({
            # "id": article.id,
            "title": article.title,
            "summary": article.summary,
            "category": article.category.name,
            # "published_at": article.published_at.isoformat() if article.published_at else None,
            "url": article.url
        })
    
    # Prepare conversation data
    conversation_data = []
    # for conv in conversations:
    #     conversation_data.append({
    #         "message": conv.message,
    #         "response": conv.response,
    #         "timestamp": conv.timestamp.isoformat()
    #     })
    
    # article_json = json.dumps(article_data, indent=2).replace("_", "\\_").replace("*", "\\*").replace("[", "\\[").replace("]", "\\]")
    
    # conversation_json = json.dumps(conversation_data, indent=2).replace("_", "\\_").replace("*", "\\*").replace("[", "\\[").replace("]", "\\]")

    
    prompt = f"""
    Create a personalized news digest for a user with the following preferences:
    - Categories: {", ".join([cat.name for cat in user.categories])}
    
    Recent conversations with the user:
    {conversation}
    
    Articles to include in the digest:
    {json.dumps(article_data, indent=2)}
    
    Create a conversational, engaging digest that:
    1. Greets the user by name ({user.first_name})
    2. Introduces the digest with a brief overview
    3. Presents the articles in a conversational way, grouped by category or theme
    4. **Present articles in a well-structured way**, grouping them by category. Use:
        - Bold headers for each category
        - Bullet points for each article
        - A short, engaging summary for each article
        - A clear, well-formatted link for each article
        
    Example:
    Category
    - Article Title
      Brief summary
      Read more](URL)  
    
    """
    # Format the digest in Markdown.
    
    logger.info(f"-------------------->LLM prompt: {prompt}")
    
    try:
        # Call the LLM API
        response = await acompletion(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful news assistant creating personalized digests."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        
        # Extract the digest text
        digest_text = response.choices[0].message.content
        logger.info(f"\n\n========Generated digest with LLM: {digest_text}")
        
        return digest_text
    except Exception as e:
        logger.error(f"Error generating digest with LLM: {e}")
        # Fall back to simple formatting
        return await format_digest(articles, personalized=True, user_name=user.first_name)

async def format_digest(articles, personalized=True, user_name=None):
    """Format articles into a digest (fallback method)"""
    # Group articles by category
    categories = {}
    for article in articles:
        category = article.category.name
        if category not in categories:
            categories[category] = []
        categories[category].append(article)
    
    # Build digest text
    digest = []
    
    # Add greeting
    if personalized and user_name:
        digest.append(f"# Good day, {user_name}!")
    else:
        digest.append("# Your Daily News Digest")
    
    digest.append("\nHere are today's top stories selected for you:\n")
    
    # Add articles by category
    for category, category_articles in categories.items():
        digest.append(f"\n## {category.title()}\n")
        
        for article in category_articles:
            digest.append(f"**{article.title}**")
            digest.append(f"{article.summary[:150]}...")
            digest.append(f"[Read more]({article.url})\n")
    
    # Add footer
    digest.append("\n---\n")
    digest.append("What topics would you like to hear more about? Just let me know!")
    
    return "\n".join(digest)