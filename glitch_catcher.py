import re
import pytz
import asyncio
import shortuuid
from db import db
from rich import print
from constants import Site
from notifier import glitch_notifier
from loguru import logger
from typing import List
from thefuzz import fuzz
from datetime import datetime, timedelta
from db_actions import exists, update, upload


ny_tz = pytz.timezone('America/New_York')

async def glitch_catcher_fanduel(data, match):
    print(f"RUNNING GLITCH CATCHER 👾 - {Site.FANDUEL.value} - for match {match}")
    print(data)
    matches = db.table("live_matches").select("*").execute()
    matches_info = [ {"name" : item['match_name'], "current_set" : item['current_set'], "source" : item['source']} for item in matches.data ]
    match_to_handle_sofascore = {}
    match_to_handle_365 = {}
    
    for item in matches_info:
        fuzz_ratio = fuzz.partial_token_sort_ratio(item['name'], match)
        if fuzz_ratio >= 70:
            print(f"{item['name']} is the same as {match}")
            names = [i['name'] for i in data if i['status'] == "OPEN"]
            if item['source'] == "SOFASCORE":
                match_to_handle_sofascore = {"current": item['current_set'], "data" : names}
            elif item['source'] == "365SCORES":
                match_to_handle_365 = {"current": item['current_set'], "data" : names}

    print("SOFASCORE: ", match_to_handle_sofascore)
    print("365SCORES: ", match_to_handle_365)

    if 'data' in match_to_handle_sofascore:
        sofascore_glitches = await get_glitches(match_to_handle_sofascore['data'], "tennis", match_to_handle_sofascore['current'])
    if 'data' in match_to_handle_365:
        scores365_glitches = await get_glitches(match_to_handle_365['data'], "tennis", match_to_handle_365['current'])

    
    if len(scores365_glitches) > 0 and len(sofascore_glitches) > 0:
        if sofascore_glitches == scores365_glitches:
            glitch = {
                "match_name" : match,
                "markets" : scores365_glitches,
                "reference" : f"{Site.SOFASCORE.value}/{Site.SCORES365.value}",
                "uuID" : shortuuid.uuid()
            }
            await database_actions(glitch=glitch)
    elif len(scores365_glitches) > 0 and len(sofascore_glitches) == 0:
        glitch = {
            "match_name" : match,
            "markets" : scores365_glitches,
            "reference" : Site.SCORES365.value,
            "uuID" : shortuuid.uuid()
        }
        await database_actions(glitch=glitch)
    elif len(sofascore_glitches) > 0 and len(scores365_glitches) == 0:
        glitch = {
            "match_name" : match,
            "markets" : sofascore_glitches,
            "reference" : Site.SOFASCORE.value,
            "uuID" : shortuuid.uuid()
        }
        await database_actions(glitch=glitch)
    else:
        print("No glitches found!")



# # # # # #

async def get_glitches(data: List[str], sport: str, current: str):
    print("Looking for glitches 🔍")
    sports_regex = {
        "baseball": [r"\d(st|nd|rd|th) inning", 0],
        "tennis": [r"Set \d", -1]
    }

    glitches = []
    regex, int_index = sports_regex[sport]
    
    if not sport in sports_regex: return None

    current_match = re.search(regex, current, flags=re.IGNORECASE)
    if not current_match: return None

    current_int = int(current_match.group()[int_index])
    
    for match in data:
        checked_match = re.search(regex, match, flags=re.IGNORECASE)
        if checked_match:
            checked_int = int(checked_match.group()[int_index])
            if checked_int < current_int:
                glitches.append(match)

    return glitches

async def database_actions(glitch):
    glitch_record_exists = await exists(table="glitches", to_match={"match_name": glitch['match_name'], "reference" : glitch['reference']})
    if glitch_record_exists:
        response = await update(table="glitches", info={"markets" : glitch["markets"]}, to_match={"match_name": glitch['match_name'], "reference" : glitch['reference']})
        print(response)
    else:
        response = await upload(table="glitches", info=glitch)

# # # # # 
async def check_glitches():
    glitches_table = db.table("glitches").select("*").execute()
    
    for glitch in glitches_table.data:
        created_at = datetime.fromisoformat(glitch['created_at'].replace('Z', '+00:00')).astimezone(ny_tz)
        if created_at < (datetime.now(ny_tz) - timedelta(minutes=2)):
            duration = datetime.now(ny_tz) - created_at  
            duration_str = str(duration).split(".")[0]
            print(f'Glitch for match: {glitch["match_name"]} {glitch["markets"]} reference: {glitch["reference"]} - has lasted: {duration_str}')
            if glitch['notification_id']:
                print("Notification already sent.")
            else:
                await glitch_notifier(glitches=glitch['markets'], match_name=glitch['match_name'], site="FanDuel", uuID=glitch['uuID'])


if __name__ == "__main__":
    asyncio.run(check_glitches())


