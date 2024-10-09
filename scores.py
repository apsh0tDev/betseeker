import asyncio
from loguru import logger
from verifier import verifier
from connection import scrape
from datetime import datetime
from sofascore import tidy_up_sofascore
from scores365 import tidy_up_365scores
from constants import Site, sofascore_url, scores365_url

async def scrape_scores_data(site, sport):
    if site == Site.SOFASCORE:
        url = sofascore_url.format(sport_name=sport)
        data = {
            'cmd' : 'request.get',
            'url' : url,
            'requestType' : 'request',
            'proxyCountry' : 'UnitedStates'
        }
        response = await scrape(data, Site.SOFASCORE.value)

        if response == None:
           logger.error(f"Could not get live scores - {Site.SOFASCORE.value}")
        else:
            is_valid = await verifier(response)
            if is_valid:
                await tidy_up_sofascore(response['solution']['response'])
            else:
                logger.error(f"Invalid response - {Site.SOFASCORE.value}")

    elif site == Site.SCORES365:
        if sport == "tennis":
            sportId = 3
        today = datetime.today().strftime('%d/%m/%Y')
        url = scores365_url.format(sportId=sportId, startDate=today, endDate=today)
        print(url)
        data = {
        'cmd' : 'request.get',
        'url' : url,
        'requestType' : 'request'
        }
        response = await scrape(data, Site.SCORES365.value)

        if response == None:
           logger.error(f"Could not get live scores - {Site.SCORES365.value}")
        else:
            is_valid = await verifier(response)
            if is_valid:
                #TODO JSON ENCODER
                await tidy_up_365scores(response['solution']['response'])
            else:
                logger.error(f"Invalid response - {Site.SCORES365.value}")

async def scrape_all():
    tasks = [scrape_scores_data(Site.SCORES365, 'tennis'), scrape_scores_data(Site.SOFASCORE, 'tennis')]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    scrape_all()