import json
import shortuuid
from rich import print
from constants import Site
from cleaners import clean
from db_actions import exists, update, upload

live_sets = ["Set 1", "Set 2", "Set 3", "Set 4", "Set 5"]

async def tidy_up_365scores(data):
    load = json.loads(data)
    live_matches = []
    matches_to_schedule = []

    matches_ids = []
    
    games = load['games'] or []
    competitions = load['competitions'] or []

    for game in games:
        if game['statusText'] == "Scheduled":
            matches_to_schedule.append(game)
        elif game['statusText'] in live_sets:
            live_matches.append(game)
        elif game['statusText'] == "Final" and 'justEnded' in game and game['justEnded'] == True:
            live_matches.append(game)

    #--- Live matches
    for match in live_matches:
        info = await get_match_info(match, competitions)
        scores_info = await get_scores(match, info['current_set'], info['uuID'])

        to_match = {
            "match_name" : info['match_name'],
            "match_id" : info['match_id'],
            "source" : info['source']
        }        
        scores_to_match = {
            "match_id" : info['match_id'],
            "source" : info['source']
        }

        matches_ids.append(info['match_id'])

        value_exists = await exists(table="live_matches", to_match=to_match)
        scoreboard_exists = await exists(table="scoreboard", to_match=scores_to_match)

        if value_exists and scoreboard_exists:
            print("Already exists. Updating")
            await update(table="live_matches", info={"current_set" : info["current_set"]}, to_match=to_match)
            await update(table="scoreboard", info={"teamA" : scores_info['teamA'], "teamB" : scores_info['teamB'], "period" : scores_info['period']}, to_match=scores_to_match)
        elif value_exists == True and scoreboard_exists == False:
            await update(table="live_matches", info={"current_set" : info["current_set"]}, to_match=to_match)
            await upload(table="scoreboard", info=scores_info)
        else:
            res_match = await upload(table="live_matches", info=info)
            res_score = await upload(table="scoreboard", info=scores_info)
            print(res_match)
            print(res_score)

    await clean(data=matches_ids, table="live_matches", source=Site.SCORES365.value)


#-- Utils
async def get_match_info(match, competitions):
    current_sets = ["Set 1", "Set 2", "Set 3", "Set 4", "Set 5", "Final"]

    info = {
        "match_id": match['id'],
        "match_name": f"{match['homeCompetitor']['name']} vs {match['awayCompetitor']['name']}",
        "uuID": shortuuid.uuid(),
        "tournament": next((item['name'] for item in competitions if item['id'] == match['competitionId']), None),
        "tournament_display_name": match['competitionDisplayName'],
        "teamA" : match['homeCompetitor']['name'],
        "teamB" : match['awayCompetitor']['name'],
        "current_set" : match['statusText'] if match['statusText'] in current_sets else 'Unknown',
        "status" : "Final" if match['statusText'] == "Final" else "Live" if match['statusText'] in current_sets else "Unknown",
        "source" : Site.SCORES365.value,
        "date" : match['startTime'],
    }
    return info

async def get_scores(match, current_set, uuID):
    info = {
        "match_id" : match['id'],
        "period" : current_set,
        "teamA" : await get_team_score(match['stages'], "homeCompetitorScore"),
        "teamB" : await get_team_score(match['stages'], "awayCompetitorScore"),
        "uuID" : uuID,
        "source" : Site.SCORES365.value
    }

    return info

async def get_team_score(stages, team):
    team_arr = []
    for item in stages:
        if item['name'] in live_sets:
            if item[team] >= 0:
                team_arr.append(str(round(item[team])))
    return team_arr