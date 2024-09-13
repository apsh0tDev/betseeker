import json
import asyncio
from db import db
from rich import print
from loguru import logger
from constants import Site
from cleaners import clean
from db_actions import exists, update, upload, db_actions
from utils import remove_parentheses, get_uuID, fix_match_name


async def tidy_up_matches(load, sport):
    matches_ids = []
    if sport == "tennis":
        if 'widgets' in load and 'payload' in load['widgets'][0] and 'fixtures' in load['widgets'][0]['payload']:
            fixtures = load['widgets'][0]['payload']['fixtures']

            for match in fixtures:
                if match['stage'] == "Live":
                    info = {
                        "match_name" : fix_match_name(remove_parentheses(match['name']['value'])),
                        "match_id" : match['id'],
                        "tournament" : match['tournament']['name']['value'],
                        "competition" : match['competition']['name']['value'],
                        "source" : Site.BETMGM.value,
                    }
                    sofa_uuID, scores365_uuID = await get_uuID(info['match_name'])
                    info['uuID'] = {
                        "SOFASCORE" : sofa_uuID,
                        "SCORES365" : scores365_uuID

                    }

                    matches_ids.append(int(match['id']))
                    to_match = { "match_id" : info['match_id'], "match_name" : info['match_name'], "source" : Site.BETMGM.value}
                    value_exists = await exists("matches_list", to_match)
                    if value_exists:
                        print("Already exists, skip")
                    else:
                        response = await upload(table="matches_list", info=info)
                        print(response)

    await clean(matches_ids, "matches_list", Site.BETMGM.value)

#---- Markets
async def handle_markets(load, sport):
    if sport == "tennis":
        if 'fixture' in load:
            match_id = load['fixture']['id']
            match_name = remove_parentheses(load['fixture']['name']['value'])
            games = load['fixture']['games']
            match_players = [remove_parentheses(load['fixture']['participants'][0]['name']['value']), remove_parentheses(load['fixture']['participants'][1]['name']['value'])]
            for game in games:
                await market_sorter(game=game,
                                match_name=match_name,
                                match_id=match_id,
                                match_players=match_players)
                
async def market_sorter(game, match_name, match_id, match_players):
    game_name = game['name']['value']
    #print(game_name)
    match game_name:
        case "Set 1 Winner":
            await regular_odds(
                game=game,
                table="set_one_winner",
                match_name=match_name,
                match_id=match_id,
                match_players=match_players
            )
        case "Set 2 Winner":
            await regular_odds(
                game=game,
                table="set_two_winner",
                match_name=match_name,
                match_id=match_id,
                match_players=match_players
            )
        case "Set 3 Winner":
            await regular_odds(
                game=game,
                table="set_three_winner",
                match_name=match_name,
                match_id=match_id,
                match_players=match_players
            )
        case "Match Winner":
            await regular_odds(
                game=game,
                table="match_winner",
                match_name=match_name,
                match_id=match_id,
                match_players=match_players
            )

async def regular_odds(game, table, match_name, match_id, match_players):
    print("Regular odds: ", table)
    info = await set_default_info(match_name=match_name, match_id=match_id, game=game)
    info['teamA'] = await set_default_odds(match_players=match_players, game=game, team=0)
    info['teamB'] = await set_default_odds(match_players=match_players, game=game, team=1)

    to_match, to_update = await get_default_options(info)
    await db_actions(to_match=to_match, to_update=to_update, info=info, table=table)

#---- Utils
async def set_default_info(match_name, match_id, game):
    info = {
        "match_id" : match_id,
        "match_name" : fix_match_name(match_name),
        "source" : Site.BETMGM.value,
        "isOpen" : True if game['visibility'] == "Visible" else False
    }
    return info

async def set_default_odds(match_players, game, team):
    odds = {
        "name" : match_players[team],
        "americanOdds" : game['results'][team]['americanOdds'],
        "decimalOdds" : game['results'][team]['odds']
    }

    return odds

async def get_default_options(info):
    to_match = { "match_name" : info['match_name'], "match_id" : info['match_id'], "source" : Site.BETMGM.value }
    to_update = { "teamA" : info['teamA'], "teamB" : info['teamB'], "isOpen": info['isOpen']}

    return to_match, to_update
