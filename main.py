from src.bot import Bot
from src.utils.logger import setup_logger
from src.health import setup_health_check
import traceback
import asyncio

logger = setup_logger('main')

async def main():
    try:
        logger.info("Starting health check endpoint...")
        await setup_health_check()
        
        logger.info("Starting bot...")
        bot = Bot()
        await bot.run()
    except Exception as e:
        logger.critical(f"Failed to start bot: {str(e)}")
        logger.critical(traceback.format_exc())
        raise

if __name__ == "__main__":
    asyncio.run(main())