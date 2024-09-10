import json
import pytz
import shortuuid
from rich import print
from thefuzz import fuzz
from cleaners import clean
from constants import Site
from datetime import datetime
from db_actions import exists, upload, update

async def tidy_up_sofascore(data):
    load = json.loads(data)
    match_ids = []
    if 'events' in load:
        for event in load['events']:
            info = {
                "match_id": event['id'],
                "match_name" : f"{event['homeTeam']['name']} vs {event['awayTeam']['name']}",
                "source" : Site.SOFASCORE.value,
                "tournament": event['tournament']['category']['name'],
                "tournament_display_name": event['tournament']['name'],
                "date": await get_date(event['startTimestamp']),
                "current_set": await get_current_set(event['status']['description']),
                "status": "Live" if event['status']['type'] == "inprogress" else "Unknown",
                "teamA": event['homeTeam']['name'],
                "teamB": event['awayTeam']['name'],
                "uuID" : shortuuid.uuid(),
            }

            scoreboard = {
                "match_id" : info['match_id'],
                "period" : info['current_set'],
                "teamA" : await get_scores(event['homeScore']),
                "teamB" : await get_scores(event['awayScore']),
                "source" : Site.SOFASCORE.value,
                "uuID" : info['uuID']
            }

            match_ids.append(event['id'])
            to_match = {
                "match_id" : str(info['match_id']),
                "source" : info['source'],
                "match_name" : info['match_name']
            }
            score_to_match = {
                "match_id" : str(scoreboard['match_id']),
                "source" : scoreboard['source'],
            }
            value_exists = await exists(table="live_matches", to_match=to_match)
            scoreboard_exists = await exists(table="scoreboard", to_match=score_to_match)

            if value_exists and scoreboard_exists:
                print("Already exists. Updating")
                await update(table="live_matches", to_match=to_match, info={"current_set" : info['current_set']})
                await update(table="scoreboard", to_match=score_to_match, info={"teamA": scoreboard['teamA'], "teamB" : scoreboard['teamB'], "period" : scoreboard['period']})
            else:
                response = await upload("live_matches", info)
                scoreboard_response = await upload("scoreboard", scoreboard)
                print(response)
                print(scoreboard_response)

    await clean(match_ids, "live_matches", Site.SOFASCORE.value)
            

#-- Utils
async def get_date(timestamp):
    dt_object = datetime.fromtimestamp(timestamp, tz=pytz.UTC)
    timestamptz_str = dt_object.isoformat()
    return timestamptz_str

async def get_current_set(set_name):
    set_names = ["Set 1", "Set 2", "Set 3", "Set 4", "Set 5"]
    for name in set_names:
        fuzz_ratio = fuzz.token_sort_ratio(name, set_name)
        if fuzz_ratio >= 80:
            current_set = name
            return current_set

async def get_scores(scores):
    periods = ['period1', 'period2', 'period3', 'period4', 'period5']
    score_keys = [item for item in scores]
    score_arr = []
    for key in score_keys:
        if key in periods:
            score_arr.append(str(scores[key]))
    return score_arr