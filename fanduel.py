from db import db
from constants import Site
from rich import print
from thefuzz import fuzz
from cleaners import clean
from db_actions import exists, update, upload
from glitch_catcher import glitch_catcher_fanduel

async def tidy_up_matches(load, sport):
    print("FANDUEL", sport)

    matches_ids = []
    if 'attachments' in load:
        if 'competitions' in load['attachments']:
            competitions = load['attachments']['competitions']
        
        if 'events' in load['attachments']:
            evs = load['attachments']['events']

        if 'markets' in load['attachments']:
            markets = load['attachments']['markets']
            market_keys = [key for key in markets]

        for key in market_keys:
            if 'inPlay' in markets[key] and markets[key]['inPlay'] == True:
                event = markets[key]
                info = {
                    "match_id": event['eventId'],
                    "match_name" : find_value(event['eventId'], evs),
                    "competition" : find_value(event['competitionId'], competitions),
                    "source" : Site.FANDUEL.value
                }
                sofa_uuID, score365_uuID = await get_uuID(info['match_name'])
                info['uuID'] = {
                    "SOFASCORE" : sofa_uuID,
                    "SCORES365" : score365_uuID
                }
                matches_ids.append(info['match_id'])
                to_match = { "match_id" : info['match_id'], "match_name" : info['match_name'], "source" : Site.FANDUEL.value}
                value_exists = await exists("matches_list", to_match)
                if value_exists:
                    print("Already exists, skip")
                else:
                    response = await upload(table="matches_list", info=info)
                    print(response)

    await clean(matches_ids, "matches_list", Site.FANDUEL.value)

async def handle_markets(load, sport):
    if 'attachments' in load and 'events' in load['attachments']:
        market_names = []
        event_key = [key for key in load['attachments']['events']]
        match_name = load['attachments']['events'][event_key[0]]['name']
        eventId = load['attachments']['events'][event_key[0]]['eventId']

        if 'markets' in load['attachments']:
            markets = load['attachments']['markets']
            markets_keys = [key for key in markets]
            for key in markets_keys:
                market = markets[key]
                market_names.append(market['marketName'])

        uuIDs = db.table("matches_list").select("*").eq("match_id", eventId).execute()
        await glitch_catcher_fanduel(market_names, match_name, uuIDs.data)
    


# -- Utils
def find_value(id, group):
    group_keys = [key for key in group]
    for key in group_keys:
        if str(id) == key:
            return group[key]['name']

def extract_players(matchup):
    return matchup.split(" v ")

async def get_uuID(match):
    print(f"Getting uuID for {match}")

    sofa_uuID = ''
    scores365_uuID = ''

    matches = db.table("live_matches").select("*").execute()
    for item in matches.data:
        fuzz_ratio = fuzz.token_sort_ratio(item['match_name'], match)
        if fuzz_ratio >= 70:
            if item['source'] == Site.SOFASCORE.value:
                sofa_uuID = item['uuID']
            elif item['source'] == Site.SCORES365.value:
                scores365_uuID = item['uuID']

    return sofa_uuID, scores365_uuID