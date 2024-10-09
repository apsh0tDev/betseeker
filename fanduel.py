from db import db
from constants import Site
from rich import print
from thefuzz import fuzz
from cleaners import clean
from utils import get_uuID, fix_match_name
from glitch_catcher import glitch_catcher_fanduel
from db_actions import exists, update, upload, db_actions
from compare_sites import is_match_behind

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
                    "match_name" : fix_match_name(find_value(event['eventId'], evs)),
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
                    await upload(table="matches_list", info=info)

    await clean(matches_ids, "matches_list", Site.FANDUEL.value)

async def handle_markets(load, sport):
    if 'attachments' in load and 'events' in load['attachments']:
        market_names = []
        event_key = [key for key in load['attachments']['events']]
        match_name = load['attachments']['events'][event_key[0]]['name']
        eventId = load['attachments']['events'][event_key[0]]['eventId']
        players = extract_players(load['attachments']['events'][event_key[0]]['name'])
        event = load['attachments']['events'][event_key[0]]
        if 'markets' in load['attachments']:
            markets = load['attachments']['markets']
            markets_keys = [key for key in markets]
            for key in markets_keys:
                market = markets[key]
                market_names.append({"name": market['marketName'], "status" : market['marketStatus']})
                await market_sorter(event, market, players, match_name)
        
        await glitch_catcher_fanduel(market_names, match_name)
    
async def market_sorter(event, market, players, match_name):
    market_name = market['marketName']
    print("FANDUEL MARKETS")
    print(market_name)
    match market_name:
        case "Set 1 Winner":
            await regular_odds(
                event=event,
                players=players,
                match_name=match_name,
                table="set_one_winner",
                market=market
            )
        case "Set 2 Winner":
            await regular_odds(
                event=event,
                players=players,
                match_name=match_name,
                table="set_two_winner",
                market=market
            )
        case "Set 3 Winner":
            await regular_odds(
                event=event,
                players=players,
                match_name=match_name,
                table="set_three_winner",
                market=market
            )
        case "Moneyline":
            await regular_odds(
                event=event,
                players=players,
                match_name=match_name,
                table="moneyline",
                market=market
            )

#----- Markets
async def regular_odds(event, players, match_name, table, market):
    #print(table)
    info = await set_default_info(event=event, match_name=match_name)
    info['isOpen'] = True if market['marketStatus'] == "OPEN" else False
    info['teamA'] = { "name" : players[0], "odds" : await set_default_odds(market['runners'], 0) }
    info['teamB'] = { "name" : players[1], "odds" : await set_default_odds(market['runners'], 1) }

    to_match, to_update = await get_default_options(info)
    await db_actions(to_match=to_match, to_update=to_update, info=info, table=table)

# -- Utils
def find_value(id, group):
    group_keys = [key for key in group]
    for key in group_keys:
        if str(id) == key:
            return group[key]['name']

def extract_players(matchup):
    return matchup.split(" v ")

async def set_default_info(event, match_name):
    info = {
        "match_id" : event['eventId'],
        "match_name" : fix_match_name(match_name),
        "source" : Site.FANDUEL.value
    }
    return info

async def set_default_odds(odds, team_number):
    win_runner_odds = odds[team_number].get('winRunnerOdds')
    if win_runner_odds:
        american_odds = win_runner_odds.get('americanDisplayOdds', {}).get('americanOdds')
        decimal_odds = win_runner_odds.get('trueOdds', {}).get('decimalOdds', {}).get('decimalOdds')
        if decimal_odds is not None:
            decimal_odds = round(decimal_odds, 2)
    else:
        american_odds = None
        decimal_odds = None

    return {
        "americanOdds": american_odds,
        "decimalOdds" : decimal_odds
    }

async def get_default_options(info):
    to_match = { "match_name" : info['match_name'], "match_id" : info['match_id'], "source" : Site.FANDUEL.value }
    to_update = { "teamA" : info['teamA'], "teamB" : info['teamB'], "isOpen": info['isOpen']}

    return to_match, to_update
