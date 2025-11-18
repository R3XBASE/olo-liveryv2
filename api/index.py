# ==================== VERCEL WEBHOOK ENDPOINT ====================
import os
import json
import logging
from typing import Any
from http import HTTPStatus

from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from telegram.error import InvalidToken

from database.db import Database, LiveryDB
from bot.handlers import BotHandlers
from livery.injection import LiveryInjector
import requests

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Global variables
app = None
handlers = None
db = None
injector = None

async def initialize():
    """Initialize bot and database on cold start"""
    global app, handlers, db, injector
    
    if app is not None:
        return
    
    try:
        # Initialize database
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL not set")
        
        db = Database(database_url)
        await db.connect()
        logger.info("Database initialized")
        
        # Load liveries cache
        livery_db = LiveryDB(db)
        await load_liveries_to_cache(livery_db)
        
        # Initialize injection engine
        injector = LiveryInjector()
        
        # Initialize Telegram bot
        token = os.environ.get('BOT_TOKEN')
        if not token:
            raise ValueError("BOT_TOKEN not set")
        
        app = Application.builder().token(token).build()
        
        # Get admin IDs
        admin_ids_str = os.environ.get('ADMIN_IDS', '')
        admin_ids = [int(x.strip()) for x in admin_ids_str.split(',') if x.strip()]
        
        # Initialize handlers
        handlers = BotHandlers(db, injector, admin_ids)
        
        # Register handlers
        app.add_handler(CommandHandler("start", handlers.start))
        app.add_handler(CommandHandler("balance", handlers.balance))
        app.add_handler(CommandHandler("profile", handlers.profile))
        
        # Admin commands
        app.add_handler(CommandHandler("addpoints", handlers.admin_addpoints))
        app.add_handler(CommandHandler("setpoints", handlers.admin_setpoints))
        app.add_handler(CommandHandler("createproduct", handlers.admin_createproduct))
        app.add_handler(CommandHandler("confirmtx", handlers.admin_confirmtx))
        app.add_handler(CommandHandler("listusers", handlers.admin_listusers))
        app.add_handler(CommandHandler("injectionlog", handlers.admin_injectionlog))
        
        # Callback handlers
        app.add_handler(CallbackQueryHandler(handlers.button_callback))
        
        logger.info("Bot handlers initialized")
        
    except Exception as e:
        logger.error(f"Initialization error: {e}")
        raise

async def load_liveries_to_cache(livery_db: LiveryDB):
    """Load liveries from online database to cache"""
    try:
        liveries_url = os.environ.get('LIVERIES_DB_URL', 'https://gist.githubusercontent.com/R3XBASE/b0b9dcde1994d25a5257d8ccfa0c7939/raw/livery_db.json')
        response = requests.get(liveries_url, timeout=10)
        response.raise_for_status()
        
        liveries_data = response.json()
        count = await livery_db.cache_liveries(liveries_data)
        logger.info(f"Cached {count} liveries")
    except Exception as e:
        logger.warning(f"Failed to cache liveries: {e}")

async def handler(request: Any) -> Any:
    """Vercel HTTP handler for webhook"""
    try:
        await initialize()
        
        # Get request data
        try:
            data = await request.json()
        except:
            return {'statusCode': HTTPStatus.BAD_REQUEST, 'body': json.dumps({'error': 'Invalid JSON'})}
        
        # Create update from webhook data
        try:
            update = Update.de_json(data, app.bot)
        except Exception as e:
            logger.error(f"Failed to create update: {e}")
            return {'statusCode': HTTPStatus.BAD_REQUEST, 'body': json.dumps({'error': 'Invalid update'})}
        
        # Process update
        await app.process_update(update)
        
        return {'statusCode': HTTPStatus.OK, 'body': json.dumps({'status': 'ok'})}
    
    except Exception as e:
        logger.error(f"Handler error: {e}")
        return {'statusCode': HTTPStatus.INTERNAL_SERVER_ERROR, 'body': json.dumps({'error': str(e)})}

# For local testing
if __name__ == "__main__":
    import asyncio
    
    class MockRequest:
        async def json(self):
            return {}
    
    asyncio.run(handler(MockRequest()))
