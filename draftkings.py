import json
import asyncio
from db import db
from loguru import logger
from constants import draftkings_live_url, Site
from connection import scrape
from utils import get_uuID
from verifier import verifier
from rich import print
from db_actions import db_actions, exists, upload

async def scrape_all_lives():
    #First delete existing tournaments - apparently the ids change
    db.table("featured_tournaments").delete().eq("source", "Draftkings").execute()

    url = draftkings_live_url.format(sportId=6)
    print(url)
    data = {
        'cmd' : 'request.get',
        'url' : url,
        'requestType' : 'request',
        'proxyCountry' : 'UnitedStates'
    }

    response = await scrape(data=data, site="DRAFTKINGS")
    if response != None and response != '':
        is_valid = await verifier(response)
        if is_valid and 'solution' in response and 'response' in response['solution']:
            print(response['solution']['response'])
            try:
                load = json.loads(response['solution']['response'])
                if 'featuredDisplayGroup' in load and 'featuredSubcategories' in load['featuredDisplayGroup']:
                    subcats = load['featuredDisplayGroup']['featuredSubcategories'][0]
                    if 'featuredEventGroupSubcategories' in subcats:
                        groups = subcats['featuredEventGroupSubcategories']
                        for group in groups:
                            info = {
                                "name" : group['eventGroupName'],
                                "key" : group['eventGroupId'],
                                "source" : "Draftkings"
                            }

                            tournament_exists = await exists("featured_tournaments", {"source" : "Draftkings", "key" : info['key']})
                            if tournament_exists:
                                print("Already in table. skip")
                            else:
                                response = await upload(table="featured_tournaments", info=info)
                                print(response)

            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON response {e}")
        else:
            logger.error(f"Invalid response - Draftkings")

async def tidy_up_matches(load, sport):
    if sport == "tennis":
        matches_ids = []
        competition = ''
        if 'leagues' in load:
            competition = load['leagues'][0]['name']
        if 'events' in load:
            for event in load['events']:
                if event['status'] == "STARTED":
                    info = {
                        "match_id" : event['id'],
                        "source" : Site.DRAFTKINGS.value,
                        "match_name" : event['name'],
                        "competition" : competition,
                    }
                    sofa_uuID, score365_uuID = await get_uuID(info['match_name'])
                    info['uuID'] = {
                        "SOFASCORE" : sofa_uuID,
                        "SCORES365" : score365_uuID
                    }
                    matches_ids.append(int(info['match_id']))
                    to_match = { "match_id" : info['match_id'], "match_name" : info['match_name'], "source" : Site.DRAFTKINGS.value}
                    value_exists = await exists("matches_list", to_match)
                    if value_exists:
                        print("Already exists, skip")
                    else:
                        res = await upload(table="matches_list", info=info)
                        print(res)

async def handle_markets(load, sport):
    if sport == "tennis":
        if 'events' in load and 'selections' in load and 'markets' in load:
            event = load['events'][0]
            match_name = event['name']
            match_id = event['id']
            players = [event['participants'][0]['name'], event['participants'][1]['name']]
      
            print("DRAFTKINGS MARKETS")
            for market in load['markets']:
                await market_sorter(match_id=match_id, match_name=match_name, players=players, market=market, selections=load['selections'])
                
async def market_sorter(match_id, match_name, players, market, selections):
    market_name = market['name']
    print(market_name)
    match market_name:
        case "1st Set":
            await regular_odds(market=market, match_id=match_id, match_name=match_name, players=players, selections=selections, table="set_one_winner")
        case "2nd Set":
            await regular_odds(market=market, match_id=match_id, match_name=match_name, players=players, selections=selections, table="set_two_winner")
        case "3rd Set":
            await regular_odds(market=market, match_id=match_id, match_name=match_name, players=players, selections=selections, table="set_three_winner")
        case "Moneyline":
            await regular_odds(market=market, match_id=match_id, match_name=match_name, players=players, selections=selections, table="moneyline")
            
async def regular_odds(market, match_id, match_name, players, selections, table):
    info = await set_default_info(match_id=match_id, match_name=match_name)
    info['teamA'] = await find_odds(selections=selections, marketId=market['id'], player=players[0])
    info['teamB'] = await find_odds(selections=selections, marketId=market['id'], player=players[1])
    info['isOpen'] = True #TODO change this

    to_match, to_update = await get_default_options(info)
    await db_actions(to_match=to_match, to_update=to_update, info=info, table=table)


#---- Utils
async def set_default_info(match_id, match_name):
    info = {
        "match_id" : match_id,
        "match_name" : match_name,
        "source" : Site.DRAFTKINGS.value,
    }
    return info

async def find_odds(selections, marketId, player):
    for selection in selections:
        if selection['marketId'] == marketId and selection['participants'][0]['name'] == player:
            odds = {
                "name" : player,
                "odds" : {
                    "decimalOdds" : selection['displayOdds']['decimal'],
                    "americanOdds" : selection['displayOdds']['american']
                }
            }
            return odds
        
async def get_default_options(info):
    to_match = { "match_name" : info['match_name'], "match_id" : info['match_id'], "source" : Site.DRAFTKINGS.value }
    to_update = { "teamA" : info['teamA'], "teamB" : info['teamB'], "isOpen": info['isOpen']}

    return to_match, to_update

if __name__ == "__main__":
    asyncio.run(scrape_all_lives())