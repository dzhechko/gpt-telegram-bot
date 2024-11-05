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

    async def start(self):
        try:
            # Start health check
            logger.info("Starting health check endpoint...")
            await self.health_check.start()
            
            # Start bot
            logger.info("Starting bot...")
            bot_task = asyncio.create_task(self.bot.run())
            self._tasks.add(bot_task)
            bot_task.add_done_callback(self._tasks.discard)
            
            # Wait for shutdown
            await self._wait_for_shutdown()

        except Exception as e:
            logger.critical(f"Failed to start application: {str(e)}")
            logger.critical(traceback.format_exc())
            raise
        finally:
            await self.stop()

    async def stop(self):
        logger.info("Stopping application...")
        
        # Cancel all tasks
        for task in self._tasks:
            task.cancel()
        
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        
        # Stop health check
        await self.health_check.stop()
        logger.info("Application stopped")

    async def _wait_for_shutdown(self):
        while not self.should_exit:
            await asyncio.sleep(1)

def handle_signals(app: Application):
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}")
        app.should_exit = True

    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, signal_handler)

async def main():
    app = Application()
    handle_signals(app)
    
    try:
        await app.start()
    except Exception as e:
        logger.critical(f"Application failed: {str(e)}")
        logger.critical(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.critical(f"Fatal error: {str(e)}")
        logger.critical(traceback.format_exc())
        sys.exit(1)