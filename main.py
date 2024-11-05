from src.bot import Bot
from src.utils.logger import setup_logger
from src.health import HealthCheck
import traceback
import asyncio
import signal
import sys

logger = setup_logger('main')

class Application:
    def __init__(self):
        self.health_check = HealthCheck()
        self.bot = Bot()
        self.should_exit = False
        self._tasks = set()
        self.bot_app = None

    async def start(self):
        try:
            # Start health check
            logger.info("Starting health check endpoint...")
            await self.health_check.start()
            
            # Start bot and store the application instance
            logger.info("Starting bot...")
            self.bot_app = await self.bot.run()
            
            # Wait for shutdown signal
            while not self.should_exit:
                await asyncio.sleep(1)

        except Exception as e:
            logger.critical(f"Failed to start application: {str(e)}")
            logger.critical(traceback.format_exc())
            raise
        finally:
            await self.stop()

    async def stop(self):
        logger.info("Stopping application...")
        
        # Stop the bot if it's running
        if self.bot_app:
            logger.info("Stopping bot...")
            await self.bot_app.stop()
            await self.bot_app.shutdown()
        
        # Stop health check
        logger.info("Stopping health check...")
        await self.health_check.stop()
        
        logger.info("Application stopped")

def handle_signals(app: Application):
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}")
        app.should_exit = True

    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, signal_handler)

def main():
    app = Application()
    handle_signals(app)
    
    try:
        asyncio.run(app.start())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.critical(f"Application failed: {str(e)}")
        logger.critical(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()