from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database import User, Article, Category
from app.database import async_session

from datetime import datetime

async def add_dummy_data(session: AsyncSession):
    # Create a new user
    user = User(telegram_id=12345, first_name="John", last_name="Doe", username="johndoe")
    session.add(user)
    
    # Create a category
    category = Category(name="Business")
    session.add(category)
    
    # Create an article
    article = Article(
        title="Business Trends in 2025",
        url="https://example.com/business-trends",
        summary="An in-depth look at the biggest trends in business in 2025.",
        published_at=datetime.utcnow(),
        source="Example News",
        category=category  # Link article to category
    )
    session.add(article)

    # Commit to the database
    await session.commit()
    return user, category, article  # return the inserted objects for verification

# Usage in your FastAPI startup or a test script
async def init_and_add_data():
    async with async_session() as session:
        await add_dummy_data(session)
        
        
if __name__ == "__main__":
    import asyncio
    asyncio.run(init_and_add_data())
