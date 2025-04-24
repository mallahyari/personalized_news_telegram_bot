# Conversational News Digest Telegram Bot

An educational project that demonstrates how to build a Telegram bot that delivers personalized news digests and engages in conversations about current events using LLMs.

## Features

- 🤖 Conversational interface powered by LLMs
- 📰 Personalized news digests based on user interests
- 🔄 Daily updates with customizable delivery time
- 💬 Natural language interaction for preference setting
- 👍 Feedback system to improve recommendations

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py               # FastAPI application
│   ├── config.py             # Configuration settings
│   ├── database.py           # Database setup and models
│   ├── telegram_handler.py   # Telegram message handling
│   ├── command_handler.py    # Bot command processing
│   ├── conversation.py       # Conversation management with LLM
│   ├── news_service.py       # News collection and processing
│   ├── recommendation.py     # Recommendation engine
│   └── scheduler.py          # Scheduled tasks
├── requirements.txt
└── .env                      # Environment variables
```

## Setup

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file based on `.env.template`
4. Create a Telegram bot using BotFather and get the token
5. Set up your webhook URL (you can use ngrok for local testing)
6. Add your news sources and OpenAI API key to the `.env` file

## Running the Bot

```
uvicorn app.main:app --reload
```

## Bot Commands

- `/start` - Start the bot and get a welcome message
- `/help` - Show available commands
- `/categories` - Set your news preferences
- `/digest` - Get your news digest immediately
- `/time` - Set your daily digest time

## Development Notes

- The bot uses SQLite for storage, which is fine for educational purposes but consider PostgreSQL for production
- OpenAI's API is used for LLM functionality, but you can replace it with other providers
- The news scraping system is basic and should be enhanced for production use
- In a production environment, you would want to add more robust error handling and logging

## Learning Opportunities

This project demonstrates:

- FastAPI webhook integration with Telegram API
- Conversational AI with LLMs
- Asynchronous Python programming
- Database modeling with SQLAlchemy
- News content processing and categorization
- Recommendation systems based on user preferences
- Task scheduling for recurring operations

## License

MIT
