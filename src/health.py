from aiohttp import web
import logging

async def health_check(request):
    return web.Response(text="OK", status=200)

async def setup_health_check(port: int = 8080):
    app = web.Application()
    app.router.add_get('/health', health_check)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    logging.info(f"Health check endpoint running on port {port}") 