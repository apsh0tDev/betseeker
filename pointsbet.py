import json
import asyncio
import constants
from db import db
from rich import print
from thefuzz import fuzz
from loguru import logger
from db_actions import exists, upload
from connection import scrape, scrape_by_site
from verifier import verifier

async def scrape_tournaments(sport):
    url = constants.pointsbet_competitions_url.format(sport=sport)
    data = {
        'cmd' : 'request.get',
        'url' : url,
        'requestType' : 'request',
        'proxyCountry' : 'UnitedStates'
    }
    response = await scrape(data, "Pointsbet")
    if response != None and response != '':
        is_valid = await verifier(response)
        if is_valid:
            load = json.loads(response['solution']['response'])
            await tidy_up_tournaments(load)
    else:
        print("Empty resppnse, try backup")

async def tidy_up_tournaments(load):
    if 'locales' in load:
        for item in load['locales']:
            if 'competitions' in item:
                for competition in item['competitions']:
                    info = {
                        "name" : competition['name'],
                        "display_name" : competition['name'],
                        "key" : competition['key'],
                        "source" : "Pointsbet"
                    }

                    tournament_exists = await exists("featured_tournaments", {"source" : "Pointsbet", "key" : info['key']})
                    if tournament_exists:
                        print("Already in table. skip")
                    else:
                        response = await upload(table="featured_tournaments", info=info)
                        print(response)

async def tidy_up_matches(load):
    print(load)

if __name__ == "__main__":
    asyncio.run(scrape_tournaments("tennis"))
        