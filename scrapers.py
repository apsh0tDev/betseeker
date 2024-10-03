import bs4
import json
import asyncio
import betmgm
import fanduel
import constants
from db import db
from rich import print
from thefuzz import fuzz
from loguru import logger
from constants import Site
from verifier import verifier_alt, verifier
from db_actions import exists, upload
from connection import scrape_by_site, scrape


#---------------
async def scrape_data(url, useAlt, site):
    response = ''
    load = None
    #--- Scraping Ant - backup
    if useAlt:
        response = await scrape_by_site(url, site, False)
        is_valid = await verifier_alt(response)
        if is_valid:
            soup = bs4.BeautifulSoup(response, 'html.parser')
            pre = soup.find("pre")
            if pre:
                try:
                    load = json.loads(pre.text)
                except json.JSONDecodeError:
                    logger.error("Invalid JSON response")
                    load = None
            else:
                logger.error("No pre found.")
        else:
            logger.error("Invalid response.")

    #---- Scrappey - regular 
    else:
        data = {
            'cmd' : 'request.get',
            'url' : url,
            'requestType' : 'request'
        }
        if site != 'BETMGM':
            data['proxyCountry'] = 'UnitedStates'
            response = await scrape(data, site)
            is_valid = verifier(response)
            if is_valid:
                try:
                    load = json.loads(response['solution']['response'])
                except json.JSONDecodeError:
                    logger.error("Invalid JSON response")
                    load = None

            else:
                logger.error("Invalid response.")

    return load
#---------------

async def scrape_by_tournament(site):
    source = site.capitalize()
    featured_tournaments = db.table("featured_tournaments").select("*").eq("source", source).execute()
    live_table = db.table("live_matches").select("*").execute()
    tournaments = [{"name" : item['name'] , "key" : item['key']} for item in featured_tournaments.data]
    live_tournaments = [f"{item['tournament']} {item['tournament_display_name']}" for item in live_table.data] 
    
    keys = []
    for tournament in tournaments:
        for item in live_tournaments:
            fuzz_ratio = fuzz.partial_token_sort_ratio(item, tournament['name'])
            if fuzz_ratio >= 70:
                keys.append(tournament['key'])

    keys = list(set(keys))
    #----- Task manager
    for key in keys:
        url = await get_url(site=site, sport="tennis", isEvent=False, isCompetition=True, task_id=key, isScores=False)
        print(url)


async def scrape_data_(site, useProxy, sport):
    url = await get_url(site, sport)
    print(url)
    response = ''
    if useProxy:
        response = await scrape_by_site(url, constants.Site.FANDUEL.value, True)
    else:
        data = {
            'cmd' : 'request.get',
            'url' : url,
            'requestType' : 'request'
        }
        response = await scrape(data, site)
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
            is_valid = await verifier(response)
            if is_valid:
                load = json.loads(response['solution']['response'])
                await handle_load(load, site, sport)
            else:
                print("Invalid response, try again") 
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
    url = await get_url(site=site, sport=sport, isEvent=True, task_id=id)
    print(url)
    response = ''
    if useProxy:
        response = await scrape_by_site(url, constants.Site.FANDUEL.value, True)
    else:
        data = {
            'cmd' : 'request.get',
            'url' : url,
            'requestType' : 'request'
        }
        response = await scrape(data, site)
    
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
            is_valid = await verifier(response)
            if is_valid:
                load = json.loads(response['solution']['response'])
                await handle_markets_load(load, site, sport)
                return "DONE"
            else:
                print("Invalid response, try again")
                return "ERROR"                
    else:
        print("None response, try again")
        return "ERROR"

#--- Sportbooks handler
async def handle_load(load, site, sport):
    match site:
        case "FANDUEL":
            await fanduel.tidy_up_matches(load, sport)
        case "BETMGM":
            await betmgm.tidy_up_matches(load, sport)
        case "POINTSBET":
            print(load)

async def handle_markets_load(load, site, sport):
    match site:
        case "FANDUEL":
            await fanduel.handle_markets(load, sport)
        case "BETMGM":
            await betmgm.handle_markets(load, sport)


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
    return url

if __name__ == "__main__":
    asyncio.run(scrape_by_tournament(constants.Site.POINTSBET.value))
