from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Table, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
import logging


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("sqlalchemy.engine.Engine")
class SQLSelectFilter(logging.Filter):
    """Custom filter to allow only 'SELECT' log messages."""
    def filter(self, record):
        return 'SELECT' in record.getMessage()
    
# logger.addFilter(SQLSelectFilter())

from app.config import DATABASE_URL

Base = declarative_base()

# Many-to-many relationship between users and categories
user_categories = Table(
    "user_categories",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("category_id", Integer, ForeignKey("categories.id"), primary_key=True)  # Correct name
)


# Many-to-many relationship between users and articles
user_interactions = Table(
    "user_interactions",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("article_id", Integer, ForeignKey("articles.id"), primary_key=True),
    Column("interaction_type", String(20)),  # "view", "like", "dislike"
    Column("timestamp", DateTime, default=datetime.utcnow)
)

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, index=True)
    first_name = Column(String(100))
    last_name = Column(String(100), nullable=True)
    username = Column(String(100), nullable=True)
    digest_time = Column(String(5), default="08:00")  # Format: "HH:MM"
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    categories = relationship("Category", secondary=user_categories, back_populates="users")  
    interactions = relationship("Article", secondary=user_interactions, back_populates="users")  
    conversations = relationship("Conversation", back_populates="user")

class Category(Base):
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, index=True)
    
    # Relationship with users
    users = relationship("User", secondary=user_categories, back_populates="categories")  

    # Articles in this category
    articles = relationship("Article", back_populates="category")

class Article(Base):
    __tablename__ = "articles"
    
    id = Column(Integer, primary_key=True)
    title = Column(String(255))
    url = Column(String(255), unique=True, index=True)
    summary = Column(Text)
    published_at = Column(DateTime)
    source = Column(String(100))
    category_id = Column(Integer, ForeignKey("categories.id"))
    
    # Relationships
    category = relationship("Category", back_populates="articles")
    users = relationship("User", secondary=user_interactions, back_populates="interactions")  

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    message = Column(Text)
    response = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="conversations")

# Create async engine and session
async_engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession)

async def init_db():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_session():
    async with async_session() as session:
        yield session

# User operations
async def get_user_by_telegram_id(session, telegram_id):
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalars().first()
    if user:
        logger.info(f"----------->User: {user.__dict__}")
    return user

async def create_user(session, telegram_id, first_name, last_name=None, username=None):
    user = User(
        telegram_id=telegram_id,
        first_name=first_name,
        last_name=last_name,
        username=username
    )
    session.add(user)
    await session.commit()
    return user

# Article operations
async def save_article(session, title, url, summary, published_at, source, category_name):
    # Get or create category
    result = await session.execute(select(Category).where(Category.name == category_name))
    category = result.scalars().first()
    
    if not category:
        category = Category(name=category_name)
        session.add(category)
    
    # Create article
    article = Article(
        title=title,
        url=url,
        summary=summary,
        published_at=published_at,
        source=source,
        category=category
    )
    session.add(article)
    await session.commit()
    return article