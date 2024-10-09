import bs4
import json
import asyncio
import betmgm
import fanduel
import pointsbet
import draftkings
import constants
from db import db
from rich import print
from thefuzz import fuzz
from loguru import logger
from constants import Site
from verifier import verifier_alt, verifier
from db_actions import exists, upload
from connection import scrape_by_site, scrape
from utils import get_data

#----- scrape main
async def scrape_info(site, url):
    print(url)
    data = await get_data(site)
    data['url'] = url
    response = await scrape(data, site)
    if response != None and response != '':
        is_valid = await verifier(response)
        if is_valid:
            if 'solution' in response and 'response' in response['solution']:
                return response['solution']['response']
        else:
            logger.error(f"Invalid response - {site}")
            return None
            
    else:
        logger.error(f"None response - {site}")

#----- end of scrape main

#----- scrape general - BetMGM, Fanduel
async def scrape_general(site, strict, sport):
    url = await get_url(site=site, sport=sport, isEvent=False, isCompetition=False, task_id='', isScores=False)
    data = await get_data(site)
    data['url'] = url
    print(data)
    response = await scrape(data=data, site=site)
    if response != None and response != '':
        is_valid = await verifier(response)
        if is_valid:
            if 'solution' in response and 'response' in response['solution']:
                if strict:
                    soup = bs4.BeautifulSoup(response['solution']['response'], 'html.parser')
                    pre = soup.find("pre")
                    if pre:
                        try:
                            load = json.loads(pre.text)
                            await handle_load(load=load, site=site, sport=sport)
                        except json.JSONDecodeError as e:
                            logger.error(f"JSON Encoding error - {e} - {site}")
                            
                    else:
                        logger.error(f"PRE not found - {site}")
                else:
                    try:
                        load = json.loads(response['solution']['response'])
                        await handle_load(load=load, site=site, sport=sport)
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON Encoding error - {e} - {site}")
                       
        else:
            logger.error(f"Invalid response - {site}")
    else:
        logger.error(f"None response - {site}")


#----- end of scrape general

#----- scrape by tournament - Draftkings, Pointsbet
async def scrape_by_tournament(site):
    source = site.capitalize()
    featured_tournaments_table = db.table("featured_tournaments").select("*").eq("source", source).execute()
    featured_tournaments = [{"name" : item['name'], "key" : item['key']} for item in featured_tournaments_table.data]

    tournaments = ["WTA", "ITF", "ATP"]
    live_tournaments_table = db.table("live_matches").select("*").execute()
    live_tournaments = [f"{item['tournament'] if item['tournament'] in tournaments else ''} {item['tournament_display_name']}" for item in live_tournaments_table.data]

    keys = []
    for tournament in featured_tournaments:
        for item in live_tournaments:
            fuzz_ratio = fuzz.partial_token_sort_ratio(item, tournament['name'])
            if fuzz_ratio >= 75:
                keys.append(tournament['key'])

    keys = list(set(keys))
    tasks = []
    for key in keys:
        url = await get_url(site=site, sport="tennis", isEvent=False, isCompetition=True, task_id=key, isScores=False)
        tasks.append(scrape_info(site, url))

    results = await asyncio.gather(*tasks, return_exceptions=True)
    for result in results:
        if result != None:
                soup = bs4.BeautifulSoup(result, 'html.parser')
                pre = soup.find("pre")
                if pre:
                    try:
                        load = json.loads(pre.text)
                        await handle_load(load=load, site=site, sport="tennis")
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON Encoding error - {e} - {site}")
                else:
                    logger.error(f"PRE not found - {site}")



#----- end of scrape by tournament

#----- scrape all events
async def scrape_events(site, strict, sport):
    print(site)
    matches = db.table("matches_list").select("*").eq("source", site).execute()
    matches_ids = [item['match_id'] for item in matches.data]

    tasks = []
    tasks_status = []

    if len(matches_ids) > 0:
        for task in matches_ids:
            tasks.append(scrape_event(task, site, strict, sport))

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

#----- end of scrape all events

#----- scrape each event
async def scrape_event(id='', site='', strict=False, sport="tennis"):
    url = await get_url(site, sport, isEvent=True, isCompetition=False, task_id=id, isScores=False)
    print(url)
    data = await get_data(site)
    data['url'] = url    
    print(data)
    response = await scrape(data, site)
    
    if response == None or response == '':
        logger.error(f"None response - {site}")
        return "ERROR"
    else:
        is_valid = await verifier(response)
        if is_valid:
            load = ''
            if strict:
                #print(response['solution']['response'])
                soup = bs4.BeautifulSoup(response['solution']['response'], 'html.parser')
                pre = soup.find("pre")
                if pre:
                    try:
                        load = json.loads(pre.text)
                        await handle_markets_load(load=load, site=site, sport=sport)
                        return "DONE"
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON Encoding error - {e} - {site}")
                else:
                    logger.error(f"PRE not found - {site}")
                    return "ERROR"
            else:
                    try:
                        load = json.loads(response['solution']['response'])
                        await handle_markets_load(load=load, site=site, sport=sport)
                        return "DONE"
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON Encoding error - {e} - {site}")
                        return "ERROR"

        else:
            logger.error(f"Invalid response - {site}")
            return "ERROR"
        
#----- end of scrape each event


#--- Sportbooks handler
async def handle_load(load, site, sport):
    match site:
        case "FANDUEL":
            await fanduel.tidy_up_matches(load, sport)
        case "BETMGM":
            await betmgm.tidy_up_matches(load, sport)
        case "POINTSBET":
            await pointsbet.tidy_up_matches(load)
        case "DRAFTKINGS":
            await draftkings.tidy_up_matches(load, sport)

async def handle_markets_load(load, site, sport):
    match site:
        case "FANDUEL":
            await fanduel.handle_markets(load, sport)
        case "BETMGM":
            await betmgm.handle_markets(load, sport)
        case "POINTSBET":
            await pointsbet.handle_markets(load, sport)
        case "DRAFTKINGS":
            await draftkings.handle_markets(load, sport)


#--- Utils
async def get_url(site, sport, isEvent=False, isCompetition=False, task_id='', isScores=False):
    url = ''
    match site:
        case "FANDUEL":
            if sport == "tennis":
                if isEvent:
                    url = constants.fanduel_event_url.format(id=task_id, tab="popular")
                elif isScores:
                    url = ''
                else:
                    url = constants.fanduel_live_url.format(eventTypeID=2)
        case "BETMGM":
            if sport == "tennis":
                if isEvent:
                    url = constants.betmgm_events.format(id=task_id)
                else:
                    url = constants.betmgm_url.format(sportId=5)
        case "POINTSBET":
            if sport == "tennis":
                if isCompetition:
                    url = constants.pointsbet_url.format(competitionId=task_id)
                if isEvent:
                    url = constants.pointsbet_event_url.format(eventId=task_id)
        case "DRAFTKINGS":
            if sport == "tennis":
                if isCompetition:
                    url = constants.draftkings_group.format(id=task_id)
                if isEvent:
                    url = constants.draftkings_event.format(eventId=task_id)
    return url

if __name__ == "__main__":
    asyncio.run(scrape_events(Site.DRAFTKINGS.value, True, "tennis"))
    #asyncio.run(scrape_by_tournament(Site.DRAFTKINGS.value))
