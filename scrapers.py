import bs4
import json
import asyncio
import fanduel
import constants
from db import db
from rich import print
from thefuzz import fuzz
from loguru import logger
from verifier import verifier_alt
from db_actions import exists, upload
from connection import scrape_by_site

async def scrape_data(site, useProxy, sport):
    url = await get_url(site, sport)
    response = ''
    if useProxy:
        response = await scrape_by_site(url, constants.Site.FANDUEL.value, True)
    
    if response != None and response != '':
        if useProxy:
            is_valid = await verifier_alt(response)
            if is_valid:
                soup = bs4.BeautifulSoup(response, 'html.parser')
                pre = soup.find("pre")
                load = json.loads(pre.text)
                await handle_load(load, site, sport)
            else:
                print("Invalid response, try again")
        else:
            print("...")
    else:
        print("None response, try again")


async def scrape_events(site, useProxy, sport):
    print(site)
    matches = db.table("matches_list").select("*").eq("source", site).execute()
    matches_ids = [item['match_id'] for item in matches.data]

    tasks = []
    tasks_status = []

    if len(matches_ids) > 0:
        for task in matches_ids:
            tasks.append(scrape_event(task, site, useProxy, sport))
            await asyncio.sleep(1)

    results = await asyncio.gather(*tasks, return_exceptions=True)
    for result in results:
        if isinstance(result, Exception):
           tasks_status.append("ERROR")
        else:
            tasks_status.append(result)
    logger.info(f"Task statuses for {site}: {tasks_status}")
    error_count = tasks_status.count("ERROR")
    if len(tasks_status) > 0:
        error_percentage = (error_count / len(tasks_status)) * 100
        if error_percentage > 45:
            error_sum = db.table("sportsbooks").select("not_available_sum").eq("name", site).execute()
            num = error_sum.data[0]['not_available_sum'] + 1        
            db.table("sportsbooks").update({"available" : False, "not_available_sum" : num}).eq("name", site).execute()
        else:
            available_sum = db.table("sportsbooks").select("available_sum").eq("name", site).execute()
            num = available_sum.data[0]['available_sum'] + 1
            db.table("sportsbooks").update({"available" : True, "available_sum" : num}).eq("name", site).execute()
    else:
        logger.info(f"No tasks for {site} at the moment.")

async def scrape_event(id, site, useProxy, sport):
    url = await get_event_url(site, sport, id)
    response = ''
    if useProxy:
        response = await scrape_by_site(url, constants.Site.FANDUEL.value, True)
    
    if response != None and response != '':
        if useProxy:
            is_valid = await verifier_alt(response)
            if is_valid:
                soup = bs4.BeautifulSoup(response, 'html.parser')
                pre = soup.find("pre")
                load = json.loads(pre.text)
                await handle_markets_load(load, site, sport)
                return "DONE"
            else:
                print("Invalid response, try again")
                return "ERROR"
        else:
            print("...")
    else:
        print("None response, try again")
        return "ERROR"


#--- Sportbooks handler
async def handle_load(load, site, sport):
    match site:
        case "FANDUEL":
            await fanduel.tidy_up_matches(load, sport)

async def handle_markets_load(load, site, sport):
    match site:
        case "FANDUEL":
            await fanduel.handle_markets(load, sport)


#--- Utils
async def get_url(site, sport):
    url = ''
    match site:
        case "FANDUEL":
            if sport == "tennis":
                url = constants.fanduel_live_url.format(eventTypeID=2)
    return url

async def get_event_url(site, sport, task_id):
    url = ''
    match site:
        case "FANDUEL":
            if sport == "tennis":
                url = constants.fanduel_event_url.format(id=task_id, tab="all")
    return url

if __name__ == "__main__":
    asyncio.run(scrape_data(constants.Site.FANDUEL.value, True, "tennis"))