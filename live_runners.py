import pytz
import asyncio
import scores
import scrapers
from loguru import logger
from constants import Site
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()
logger.add("arbitrages.log", filter=lambda record: "arbitrage" in record["extra"], rotation="2 weeks")
logger.add("glitches.log", filter=lambda record: "glitch" in record["extra"], rotation="2 weeks")
logger.add("info.log", level="INFO", rotation="2 weeks")
logger.add("errors.log", level="WARNING", rotation="2 weeks")

async def running():
    tasks = [
        scores.scrape_scores_data(Site.SCORES365, 'tennis'),
        scores.scrape_scores_data(Site.SOFASCORE, 'tennis')
    ]
    await asyncio.gather(*tasks)


job_defaults = {
    'coalesce': False,
    'max_instances': 100,
}
scheduler.configure(job_defaults=job_defaults)
scheduler.add_job(running, 'interval', seconds=40)


try:
    scheduler.start()
    asyncio.get_event_loop().run_forever()
except (KeyboardInterrupt, SystemExit):
    pass
