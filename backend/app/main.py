import logging
from fastapi import FastAPI, Request, Depends
from app.config import TELEGRAM_TOKEN, WEBHOOK_URL
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
from app.telegram_handler import bot, process_telegram_update
from app.database import init_db, get_session
from app.scheduler import start_scheduler, stop_scheduler
from telegram import Bot, Update

import nltk
nltk.download('punkt_tab')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# bot = Bot(token=TELEGRAM_TOKEN)



@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown events."""
    # Initialize database
    await init_db()
    await bot.set_webhook(f"{WEBHOOK_URL}/webhook")
    # Start the scheduler
    # start_scheduler() # Run it only once at application startup
    logger.info("Application started")
    
    try:
        yield  # Application is running
    finally:
        stop_scheduler()

app = FastAPI(title="News Digest Telegram Bot", lifespan=lifespan)



@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "News AI Agent is running"}


@app.post("/webhook")
async def telegram_webhook(request: Request, session: AsyncSession = Depends(get_session)):
    # Get the Telegram update as JSON
    update_data = await request.json()
    logger.info(f"Received Telegram update: {update_data}")
    
    # Process the update
    try:
        await process_telegram_update(update_data, session)
    except Exception as e:
        logger.error(f"Error processing update: {e}", exc_info=True)
    
    # Always return 200 OK to Telegram
    return {"status": "ok"}



if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=9000, reload=True)