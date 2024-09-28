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

async def scrape_main(site: str, useProxy: bool, sport:str, liveEvents: bool):
    url = await get_url(site=site, sport=sport, isEvent=False, isCompetition=False, task_id='', isScores=False, liveEvents=False)
    load = await get_data(url, False, site)
    if load != None:
        await handle_load(load=load, site=site, sport=sport, liveEvents=liveEvents)

async def scrape_group(site: str, useProxy: bool, sport:str, liveEvents: bool):
    source = site.capitalize()
    featured_tournaments = db.table("featured_tournaments").select("*").eq("source", source).execute()
    tournaments = [{"name" : item['name'], "key" : item['key']} for item in featured_tournaments.data]
    if liveEvents:
        live_tournaments = db.table("live_matches").select("*").execute()
        live_names = [f"{item['tournament']} - {item['tournament_display_name']}" for item in live_tournaments.data]

    

async def scrape_data(site, useProxy, sport):
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
async def handle_load(load, site, sport, liveEvents):
    site_modules = {
        "FANDUEL" : fanduel,
        "BETMGM" : betmgm,
    }
    if site in site_modules:
        await getattr(site_modules[site], "tidy_up_matches")(load, sport, liveEvents)
    else:
        print("MODULE NOT FOUND.")
        
async def handle_markets_load(load, site, sport):
    match site:
        case "FANDUEL":
            await fanduel.handle_markets(load, sport)
        case "BETMGM":
            await betmgm.handle_markets(load, sport)


#--- Utils
async def get_url(site='', sport="tennis", isEvent=False, isCompetition=False, task_id='', isScores=False, liveEvents=False):
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
    return url

#-----
async def get_data(url, useProxy, site):
    load = ''
    if useProxy:
        response = await scrape_by_site(url, site, True)
        is_valid = await verifier_alt(response)
        if is_valid:
            soup = bs4.BeautifulSoup(response, 'html.parser')
            pre = soup.find("pre")
            if pre:
                try:
                    load = json.loads(pre.text)
                except json.JSONDecodeError:
                    print(f"Invalid JSON response - {site}")
                    load = None
            else:
                print(f"Pre not found - {site}")
    else:
        data = {
            'cmd' : 'request.get',
            'url' : url,
            'requestType' : 'request'
        }
        if site != "BETMGM": data['proxyCountry'] = 'UnitedStates'
        response = await scrape(data, site)
        is_valid = await verifier(response)
        if is_valid:
            try:
                load = json.loads(response['solution']['response'])
            except json.JSONDecodeError:
                print(f"Invalid JSON response - {site}")
                load = None
        else:
            print(f"Invalid response {site}")
    return load

if __name__ == "__main__":
    asyncio.run(scrape_group(site=Site.POINTSBET.value, useProxy=False, sport="tennis", liveEvents=True))
