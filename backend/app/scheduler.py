
from app.database import async_session, User
from app.news_service import fetch_news
from app.recommendation import generate_digest_for_user
from app.telegram_handler import bot
from app.config import NEWS_UPDATE_INTERVAL
from telegram.constants import ParseMode
from sqlalchemy.future import select
from datetime import datetime
import logging
import asyncio
import schedule
import time
import threading
import atexit

scheduler_running = True  # Global flag to control the scheduler

logger = logging.getLogger(__name__)



async def update_news():
    """Update news articles from sources, handling errors gracefully"""
    logger.info("Updating news articles...")

    try:
        async with async_session() as session:
            await fetch_news(session)
        logger.info("News update complete")
    except Exception as e:
        logger.error(f"Error updating news: {e}", exc_info=True)


async def send_daily_digests():
    """Send daily digests to users"""
    logger.info("Sending daily digests...")
    
    # Get current time in HH:MM format
    current_time = datetime.now().strftime("%H:%M")
    
    # Get users who should receive digests at this time
    async with async_session() as session:
        result = await session.execute(
            select(User).where(
                User.digest_time == current_time,
                User.is_active == True
            )
        )
        users = result.scalars().all()
    
    # Send digest to each user
    for user in users:
        try:
            # Generate digest
            digest = await generate_digest_for_user(user.id, session)
            
            if digest:
                # Send digest
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=digest,
                    parse_mode=ParseMode.MARKDOWN_V2
                )
                logger.info(f"Sent digest to user {user.id}")
            else:
                logger.error(f"Failed to generate digest for user {user.id}")
        except Exception as e:
            logger.error(f"Error sending digest to user {user.id}: {e}")
    
    logger.info("Daily digest sending complete")

def run_scheduler():
    """Run the scheduler loop and allow stopping"""
    while scheduler_running:
        schedule.run_pending()
        time.sleep(1)

def start_scheduler():
    """Set up and start the scheduler"""
    
    loop = asyncio.get_event_loop()
    
    schedule.every(NEWS_UPDATE_INTERVAL).minutes.do(
        lambda: loop.create_task(update_news())
    )
    
    for hour in range(24):
        for minute in [0, 30]:
            schedule_time = f"{hour:02d}:{minute:02d}"
            schedule.every().day.at(schedule_time).do(
                lambda: loop.create_task(send_daily_digests())
            )
    
    loop.create_task(update_news())

    global scheduler_thread
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.daemon = True  # Allows FastAPI to exit cleanly
    scheduler_thread.start()

# Ensure scheduler stops when FastAPI shuts down
def stop_scheduler():
    global scheduler_running
    scheduler_running = False
    if scheduler_thread.is_alive():
        scheduler_thread.join()  # Ensure it stops cleanly

atexit.register(stop_scheduler)