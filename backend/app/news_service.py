import logging
import asyncio
from datetime import datetime, timedelta
import newspaper
from newspaper import Article
from sqlalchemy.future import select

from app.config import NEWS_SOURCES, NEWS_CATEGORIES
from app.database import save_article, Article as ArticleModel, Category

logger = logging.getLogger(__name__)

async def fetch_news(session):
    """Fetches news from configured sources"""
    for source_url in NEWS_SOURCES:
        try:
            # Build newspaper source
            source = newspaper.build(source_url, memoize_articles=False)
            
            total_articles = len(source.article_urls())
            logger.info(f"---------->Found {total_articles} articles from {source_url}")
            
            # Get articles
            for article_url in source.article_urls()[:300]:
                try:
                    # Parse article
                    article = Article(article_url)
                    article.download()
                    article.parse()
                    article.nlp()  # This extracts keywords, summary, etc.
                    
                    # Determine category
                    category = await categorize_article(article)
                    
                    # Save to database
                    await save_article_to_db(
                        title=article.title,
                        url=article_url,
                        summary=article.summary,
                        published_at=article.publish_date or datetime.utcnow(),
                        source=source_url,
                        category=category,
                        session=session
                    )
                except Exception as e:
                    logger.error(f"Error processing article {article_url}: {e}")
        except Exception as e:
            logger.error(f"Error fetching news from {source_url}: {e}")

async def categorize_article(article):
    """Categorize an article into one of the predefined categories"""
    # This is a simplified approach. In a production system, you would use
    # a more sophisticated NLP-based categorization
    
    keywords = article.keywords
    title_lower = article.title.lower()
    text_lower = article.text.lower()
    
    # Simple keyword matching
    for category in NEWS_CATEGORIES:
        if category in keywords or category in title_lower or category in text_lower:
            return category
    
    # Default category if no match
    return "general"

async def save_article_to_db(title, url, summary, published_at, source, category, session):
    """Save an article to the database"""
    # Check if article already exists
    result = await session.execute(
        select(ArticleModel).where(ArticleModel.url == url)
    )
    existing_article = result.scalars().first()
    
    if not existing_article:
        # Save new article
        await save_article(
            session=session,
            title=title,
            url=url,
            summary=summary,
            published_at=published_at,
            source=source,
            category_name=category
        )
        logger.info(f"Saved new article: {title}")
    else:
        logger.debug(f"Article already exists: {title}")

async def get_recent_articles_by_category(session, category, limit=10):
    """Get recent articles for a specific category"""
    # Get category ID
    result = await session.execute(
        select(Category).where(Category.name == category)
    )
    category_obj = result.scalars().first()
    
    if not category_obj:
        return []
    
    # Get articles
    result = await session.execute(
        select(ArticleModel)
        .where(ArticleModel.category_id == category_obj.id)
        .order_by(ArticleModel.published_at.desc())
        .limit(limit)
    )
    articles = result.scalars().all()
    logger.info(f"#######################Found {len(articles)} articles for user {articles}")
    return articles

async def get_articles_for_digest(session, user_categories, limit_per_category=2):
    """Get articles for a user's digest based on their preferences"""
    articles = []
    
    # Get articles for each category
    for category in user_categories:
        logger.info(f"****************Getting articles for category: {category.name}")
        category_articles = await get_recent_articles_by_category(
            session, 
            category.name, 
            limit=limit_per_category
        )
        articles.extend(category_articles)
        # logger.info(f"#######################Found {len(category_articles)} articles for user {category_articles.__dict__}")
    
    # Sort by publication date
    articles.sort(key=lambda x: x.published_at, reverse=True)
    
    # Limit total number of articles
    return articles[:limit_per_category * len(user_categories)]