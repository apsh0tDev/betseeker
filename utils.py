import re
import pytz
from db import db
from thefuzz import fuzz
from datetime import datetime
from constants import Site

def get_current_ny_time():
    # Define New York timezone
    ny_tz = pytz.timezone('America/New_York')
    ny_time = datetime.now(ny_tz)
    return ny_time.strftime('%Y-%m-%d %I:%M %p')

def format_datetime(input_datetime_str):
    input_datetime = datetime.fromisoformat(input_datetime_str.replace('Z', '+00:00'))
    ny_timezone = pytz.timezone('America/New_York')
    input_datetime = input_datetime.astimezone(ny_timezone)
    current_datetime = datetime.now(ny_timezone)
    day_difference = (input_datetime.date() - current_datetime.date()).days
    if day_difference == 0:
        day_str = "Today"
    elif day_difference == 1:
        day_str = "Tomorrow"
    else:
        day_str = input_datetime.strftime("%A")
    time_str = input_datetime.strftime("%I:%M %p")

    return f"{day_str} - {time_str}"

def remove_parentheses(text):
    return re.sub(r'\([^)]*\)', '', text)

async def get_uuID(match):
    print(f"Getting uuID for {match}")

    sofa_uuID = ''
    scores365_uuID = ''

    matches = db.table("live_matches").select("*").execute()
    for item in matches.data:
        fuzz_ratio = fuzz.partial_token_sort_ratio(item['match_name'], match)
        if fuzz_ratio >= 70:
            if item['source'] == Site.SOFASCORE.value:
                sofa_uuID = item['uuID']
            elif item['source'] == Site.SCORES365.value:
                scores365_uuID = item['uuID']

    return sofa_uuID, scores365_uuID

def fix_match_name (match_name:str):
    until_vs = re.match(r"[a-zA-Z /\.]+ (v|-) ", match_name)
    if (until_vs):
        name1 = match_name[:(until_vs.span()[1] - 3)]
        name2 = match_name[(until_vs.span()[1]):]
        match_name = f"{name1} vs {name2}"
    return match_name

