import re
import pytz
from db import db
from rich import print
from constants import Site
from notifier import glitch_notifier
from loguru import logger
from typing import List
from thefuzz import fuzz
from datetime import datetime, timedelta

ny_tz = pytz.timezone('America/New_York')

async def glitch_catcher_fanduel(data, match):
    print(f"RUNNING GLITCH CATCHER 👾 - {Site.FANDUEL.value} - for match {match}")
    # print(data)
    # print(match)

    matches = db.table("live_matches").select("*").execute()
    matches_info = [ {"name" : item['match_name'], "current_set" : item['current_set']} for item in matches.data ]
    glitches = []
    
    for match in matches_info:
        fuzz_ratio = fuzz.partial_token_sort_ratio(match['name'], match)
        if fuzz_ratio >= 70:
            print(f"{match['name']} is the same as {match}")
            data = [item['name'] for item in data if item['status'] == 'OPEN']
            glitches = await get_glitches(data, "tennis", match['current_set'])
            print(glitches)

async def get_glitches (data: List[str], sport:str, current:str):
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