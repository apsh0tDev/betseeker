import re
from db import db
from constants import Site
from notifier import glitch_notifier

async def glitch_catcher_fanduel(markets, match, uuIDs):
    print(f"RUNNING GLITCH CATCHER 👾 - {Site.FANDUEL.value}")
    sets = ["Set 1", "Set 2", "Set 3", "Set 4", "Set 5", "Final"]
    data = markets
    print(match)
    print(data)
    glitches_sofascore = []
    glitches_scores365 = []
    sofacore_uuID = uuIDs[0]['uuID']['SOFASCORE']
    scores365_uuID = uuIDs[0]['uuID']['SCORES365']

    if sofacore_uuID != '':
        sofascore_table = db.table("live_matches").select("*").eq("uuID", sofacore_uuID).execute()
        current_sofascore_set = sofascore_table.data[0]['current_set']
        print("Sofascore current set: ", current_sofascore_set)
        for item in data:
            data_set = re.search(r"Set \d|Final", item)
            if data_set and sets.index(data_set.group()) < sets.index(current_sofascore_set):
                glitches_sofascore.append(item)
    else:
        print("No match found for sofascore")
        
    if scores365_uuID != '':
        scores365_table = db.table("live_matches").select("*").eq("uuID", scores365_uuID).execute()
        current_scores365_set = scores365_table.data[0]['current_set']
        print("365 scores current set: ", current_scores365_set)
        for item in data:
            data_set = re.search(r"Set \d|Final", item)
            if data_set and sets.index(data_set.group()) < sets.index(current_scores365_set):
                glitches_scores365.append(item)
    else:
        print("No match found for 365scores")

    if len(glitches_sofascore) == 0 and len(glitches_scores365) == 0:
        print("No glitches found.")

    if len(glitches_sofascore) > 0:
        print("Glitches found for sofascore!")
        print(glitches_sofascore)
        await glitch_notifier(glitches_sofascore, current_sofascore_set, Site.FANDUEL.value, "Sofascore")

    if len(glitches_scores365) > 0:
        print("Glitches found for 365scores!")
        print(glitches_scores365)
        await glitch_notifier(glitches_scores365, current_scores365_set, Site.FANDUEL.value, "365Scores")




        

    
    
        