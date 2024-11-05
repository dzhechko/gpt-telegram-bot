from aiohttp import web
import logging
from aiohttp.web_runner import AppRunner, TCPSite

class HealthCheck:
    def __init__(self, port: int = 8080):
        self.port = port
        self.app = web.Application()
        self.app.router.add_get('/health', self.health_check)
        self.runner = None
        self.site = None

    async def health_check(self, request):
        return web.Response(text="OK", status=200)

    async def start(self):
        self.runner = AppRunner(self.app)
        await self.runner.setup()
        self.site = TCPSite(self.runner, '0.0.0.0', self.port)
        await self.site.start()
        logging.info(f"Health check endpoint running on port {self.port}")

    async def stop(self):
        if self.runner:
            await self.runner.cleanup()
    