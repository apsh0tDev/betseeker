import scrapers
import asyncio
from constants import Site
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()
async def line_scrapers():
    tasks = [
        scrapers.scrape_events(site=Site.FANDUEL.value, strict=True, sport="tennis"),
        scrapers.scrape_events(site=Site.BETMGM.value, strict=False, sport="tennis"),
        scrapers.scrape_events(site=Site.POINTSBET.value, strict=True, sport="tennis"),
        scrapers.scrape_events(site=Site.DRAFTKINGS.value, strict=True, sport="tennis")
    ]
    await asyncio.gather(*tasks)

async def data_scrapers():
    print("--------- RUNNING GENERAL DATA SCRAPERS ---------")
    tasks = [
        scrapers.scrape_general(site=Site.FANDUEL.value, strict=True, sport="tennis"),
        scrapers.scrape_general(site=Site.BETMGM.value, strict=False, sport="tennis"),
        scrapers.scrape_by_tournament(site=Site.POINTSBET.value),
        scrapers.scrape_by_tournament(site=Site.DRAFTKINGS.value)
    ]
    await asyncio.gather(*tasks)

job_defaults = {
    'coalesce': False,
    'max_instances': 100,
}
scheduler.add_job(line_scrapers, 'interval', seconds=40)
scheduler.add_job(data_scrapers, 'interval', minutes=2)

try:
    scheduler.start()
    asyncio.get_event_loop().run_forever()
except (KeyboardInterrupt, SystemExit):
    pass