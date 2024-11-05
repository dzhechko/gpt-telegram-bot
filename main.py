from src.bot import Bot
from src.utils.logger import setup_logger
from src.health import HealthCheck
import traceback
import asyncio
import signal

logger = setup_logger('main')

class Application:
    def __init__(self):
        self.health_check = HealthCheck()
        self.bot = Bot()
        self.should_exit = False

    async def start(self):
        try:
            # Start health check
            logger.info("Starting health check endpoint...")
            await self.health_check.start()
            
            # Start bot
            logger.info("Starting bot...")
            await self.bot.run()

        except Exception as e:
            logger.critical(f"Failed to start application: {str(e)}")
            logger.critical(traceback.format_exc())
            raise

    async def stop(self):
        logger.info("Stopping application...")
        await self.health_check.stop()
        # Bot cleanup will be handled by its own stop method

def handle_signals():
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(shutdown(loop, sig)))

async def shutdown(loop, signal):
    logger.info(f"Received exit signal {signal.name}...")
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    [task.cancel() for task in tasks]
    logger.info(f"Cancelling {len(tasks)} outstanding tasks")
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()

def main():
    app = Application()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        handle_signals()
        loop.run_until_complete(app.start())
        loop.run_forever()
    except Exception as e:
        logger.critical(f"Application failed: {str(e)}")
        logger.critical(traceback.format_exc())
    finally:
        loop.close()
        logger.info("Application shutdown complete.")

if __name__ == "__main__":
    main()