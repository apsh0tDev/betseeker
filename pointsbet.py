import json
import asyncio
import constants
from db import db
from rich import print
from thefuzz import fuzz
from loguru import logger
from db_actions import exists, upload
from connection import scrape
from utils import get_uuID, decimal_to_american, get_data
from verifier import verifier
from cleaners import clean
from db_actions import db_actions

async def scrape_tournaments(sport):
    url = constants.pointsbet_competitions_url.format(sport=sport)
    data = await get_data(constants.Site.POINTSBET.value)
    data['url'] = url
    response = await scrape(data, "Pointsbet")
    if response != None and response != '':
        is_valid = await verifier(response)
        if is_valid:
            load = json.loads(response['solution']['response'])
            await tidy_up_tournaments(load)
    else:
        print("Empty resppnse, try backup")

async def tidy_up_tournaments(load):
    if 'locales' in load:
        for item in load['locales']:
            if 'competitions' in item:
                for competition in item['competitions']:
                    info = {
                        "name" : competition['name'],
                        "display_name" : competition['name'],
                        "key" : competition['key'],
                        "source" : "Pointsbet"
                    }

                    tournament_exists = await exists("featured_tournaments", {"source" : "Pointsbet", "key" : info['key']})
                    if tournament_exists:
                        print("Already in table. skip")
                    else:
                        response = await upload(table="featured_tournaments", info=info)
                        print(response)

async def tidy_up_matches(load):
    matches_ids = []
    if 'events' in load:
        for event in load['events']:
            if 'isLive' in event and event['isLive'] == True:
                info = {
                    "match_id" : event['key'],
                    "source" : constants.Site.POINTSBET.value,
                    "match_name" : event['name'],
                    "competition" : event['competitionName'],
                }
                
                sofa_uuID, score365_uuID = await get_uuID(info['match_name'])
                info['uuID'] = {
                    "SOFASCORE" : sofa_uuID,
                    "SCORES365" : score365_uuID
                }
                matches_ids.append(int(info['match_id']))
                to_match = { "match_id" : info['match_id'], "match_name" : info['match_name'], "source" : constants.Site.POINTSBET.value}
                value_exists = await exists("matches_list", to_match)
                if value_exists:
                    print("Already exists, skip")
                else:
                    res = await upload(table="matches_list", info=info)
                    print(res)
    
    await clean(matches_ids, "matches_list", constants.Site.POINTSBET.value)

async def handle_markets(load, sport):
    if sport == "tennis":
        if 'fixedOddsMarkets' in load:
            match_id = load['key']
            match_name = load['name']
            players = [load['homeTeam'], load['awayTeam']]
            for market in load['fixedOddsMarkets']:
                await market_sorter(market, match_id, match_name, players)
                
async def market_sorter(market, match_id, match_name, players):
    print("POINTSBET MARKETS")
    market_name = market['eventName']
    print(market_name)
    match market_name:
        case "1st Set Winner":
            await regular_odds(market, match_id, match_name, players, "set_one_winner")
        case "2nd Set Winner":
            await regular_odds(market, match_id, match_name, players, "set_two_winner")
        case "3rd Set Winner":
            await regular_odds(market, match_id, match_name, players, "set_three_winner")
        case "Match Result":
            await regular_odds(market, match_id, match_name, players, "match_winner")

async def regular_odds(market, match_id, match_name, players, table):
   info = await set_default_info(match_id, match_name)
   info['isOpen'] = True if market['isOpenForBetting'] == True else False
   info['teamA'] = {
       "name" : market['outcomes'][0]['name'],
       "odds" : {
           "decimalOdds" : round(market['outcomes'][0]['price'],2),
           "americanOdds" : round(decimal_to_american(market['outcomes'][0]['price']))
       }
   }
   info['teamB'] = {
       "name" : market['outcomes'][1]['name'],
       "odds" : {
           "decimalOdds" : round(market['outcomes'][1]['price'],2),
           "americanOdds" : round(decimal_to_american(market['outcomes'][1]['price']))
       }       
   }

   to_match, to_update = await get_default_options(info)
   await db_actions(to_match=to_match, to_update=to_update, info=info, table=table)

#----- Utils

async def set_default_info(match_id, match_name):
    info = {
        "match_id" : match_id,
        "match_name" : match_name,
        "source" : constants.Site.POINTSBET.value,
    }
    return info

async def get_default_options(info):
    to_match = { "match_name" : info['match_name'], "match_id" : info['match_id'], "source" : constants.Site.POINTSBET.value }
    to_update = { "teamA" : info['teamA'], "teamB" : info['teamB'], "isOpen": info['isOpen']}

    return to_match, to_update

if __name__ == "__main__":
    asyncio.run(scrape_tournaments("tennis"))
        