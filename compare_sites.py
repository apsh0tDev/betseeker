from typing import List
from db import db
from rich import print
from thefuzz import fuzz
from constants import Site

def get_matches_by_name (match_name:str, sources:List[str]=[]) -> dict:
    all_matches = db.table("live_matches").select("*")

    scores = {}

    if sources:
        filters = [ f"source.eq.{src}" for src in sources ]
        all_matches = all_matches.or_(",".join(filters))

    all_matches = all_matches.execute()

    for match in all_matches.data:
        match_percent = fuzz.partial_token_sort_ratio(match_name, match["match_name"])
        if match_percent >= 70:
            res_scoreboard = (
                db.table("scoreboard")
                .select("*")
                .eq("match_id", match["match_id"])
                .execute()
            )

            for m in res_scoreboard.data:
                m["match_name"] = match["match_name"]
                source = m["source"]
                if source not in scores:
                    scores[source] = m

    return scores

async def is_match_behind(this_match:dict): # required keys: 'teamA', 'teamB', 'match_name'

    other_matches = get_matches_by_name(this_match["match_name"], [Site.SOFASCORE.value, Site.SCORES365.value])
    this_score = [this_match["teamA"], this_match["teamB"]]

    updated_matches = []

    if Site.SOFASCORE.value in other_matches:
        updated_matches.append(other_matches[Site.SOFASCORE.value])
    if Site.SCORES365.value in other_matches:
        updated_matches.append(other_matches[Site.SCORES365.value])

    is_behind = False

    for u_match in updated_matches:
        u_score = [u_match["teamA"], u_match["teamB"]]

        if this_score != u_score:
            is_behind = True

    return is_behind
