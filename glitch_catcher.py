import re
import pytz
from db import db
from rich import print
from constants import Site
from notifier import glitch_notifier
from loguru import logger
from typing import List
from thefuzz import fuzz
from datetime import datetime, timezone, timedelta
import shortuuid

ny_tz = pytz.timezone('America/New_York')

async def glitch_catcher_fanduel(data, match, uuIDs):
    print(f"RUNNING GLITCH CATCHER 👾 - {Site.FANDUEL.value}")

    sofacore_uuID = uuIDs[0]['uuID']['SOFASCORE']
    scores365_uuID = uuIDs[0]['uuID']['SCORES365']

    if sofacore_uuID != '':
        sofascore_table = db.table("live_matches").select("*").eq("uuID", sofacore_uuID).execute()
        if len(sofascore_table) > 0:
            current_sofascore_set = sofascore_table.data[0]['current_set']
            sofascore_glitches = await get_glitches(data=data, sport="tennis", current=current_sofascore_set)
        else:
            print("No match found for sofascore")
    else:
        print("No match found for sofascore")
            
    if scores365_uuID != '':
        scores365_table = db.table("live_matches").select("*").eq("uuID", scores365_uuID).execute()
        if len(scores365_table) > 0:
           current_scores365_set  = scores365_table.data[0]['current_set']
           scores365_glitches = await get_glitches(data=data, sport="tennis", current=current_scores365_set)
        else:
            print("No match found for 365scores")
    else:
        print("No match found for 365scores")

    await handle_glitches(glitches_sofascore=sofascore_glitches, glitches_scores365=scores365_glitches, match=match)

async def get_glitches (data: List[str], sport:str, current:str):
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

async def handle_glitches(glitches_sofascore, glitches_scores365, match):
    if not glitches_sofascore and not glitches_scores365:
        logger.bind(glitch=True).info(f'No glitches found for match: {match}')
        return

    if glitches_sofascore:
        logger.bind(glitch=True).info(f'Glitches found! for match: {match} {glitches_sofascore} reference: {Site.SOFASCORE.value}')
        
    if glitches_scores365:
        logger.bind(glitch=True).info(f'Glitches found! for match: {match} {glitches_scores365} reference: {Site.SCORES365.value}')


async def db_actions(match_name, glitches, reference, similarity_threshold=80):
    glitches_table = db.table("glitches").select("*").execute()
    glitches_data = glitches_table.data

    matching_glitch = None

    for item in glitches_data:
        if fuzz.partial_token_sort_ratio(item['match_name'], match_name['match_name']) >= similarity_threshold:
            matching_glitch = item
            break
        if matching_glitch:
            # Update existing glitch record    
            res = db.table("glitches").update({
                    'markets': glitches
                }).eq('match_name', match_name).execute()

            print(f"Update record - ", res)
        else:
            # Insert new arbitrage record
            res = db.table("glitches").insert({
                'match_name': match_name,
                'markets': glitches,
                'reference': reference,
                'uuID' : shortuuid.uuid(),
            }).execute()
            print(f"New record - ", res)

async def check_db_glitches():
    # Fetch all records from the glitches table
    response = db.table("glitches").select("*").execute()
    glitches_table = response.data if response.data else []

    for glitch in glitches_table:
        created_at = datetime.fromisoformat(glitch['created_at'].replace('Z', '+00:00')).astimezone(ny_tz)
        if created_at > (datetime.now(ny_tz) - timedelta(minutes=2)):
            duration = datetime.now(ny_tz) - created_at  # Calculate duration
            # Format duration as hours, minutes, and seconds
            duration_str = str(duration).split(".")[0]  # Get string representation without microseconds
            logger.bind(glitch=True).info(f'Glitch for match: {glitch["match_name"]} {glitch["markets"]} reference: {glitch["reference"]} - has lasted: {duration_str}')
            if glitch['notification_id']:
                return
            else:
                await glitch_notifier(glitches=glitch['markets'], match_name=glitch['match_name'], site="FanDuel") #TODO

            



    




        

    
    
        