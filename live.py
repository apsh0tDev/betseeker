import random
import textwrap
import discord
import asyncio
from db import db
from loguru import logger
from tabulate import tabulate

async def get_live_matches(site):
    live_matches = db.table("live_matches").select("*").eq("source", site).execute()
    scoreboard = db.table("scoreboard").select("*").eq("source", site).execute()

    if len(live_matches.data) > 0 and len(scoreboard.data) > 0:
        formatted = await format_live_matches(live_matches.data, scoreboard.data)
        try:
            embeds = []
            for tournament in formatted:
                current_embed = discord.Embed(title=tournament['tournament'].upper(), color=random.randint(0, 0xFFFFFF))
                for block in tournament['blocks']:
                    current_embed.add_field(name="", value=textwrap.dedent(block), inline=False)
                embeds.append(current_embed)
            return embeds 
        except Exception as e:
            logger.error(f"There was an error formatting the message: {e}")    
            return None
    else:
        return None

async def format_live_matches(data, scores):
    logger.info("Formatting live table for discord")
    group = await group_matches(data, scores)
    if len(group) > 0:
        code_blocks = []
        for tournament in group:
            info = {
                "tournament" : tournament['tournament']
            }
            blocks = []
            for match in tournament['events']:
                formatted = await format_tournament(match=match)
                table_output = "\n".join(formatted)
                code_block = f"""```{table_output}
                ```"""
                blocks.append(code_block)
            info['blocks'] = blocks
            code_blocks.append(info)
        return code_blocks
    
#--- Groups matches by tournament
async def group_matches(data, scores):
    merged_list = []

    scores_dict = {}

    for score in scores:
        if 'match_id' in score:
            scores_dict[score['match_id']] = score
        else:
            logger.warning(f"Score entry missing 'match_id': {score}")

    for item in data:
            tournament_exists = False
            match_id = item.get('match_id')
            info = {
                "match_name" : item['match_name'],
                "teamA" : item['teamA'],
                "teamB" : item['teamB']
            }

            if match_id in scores_dict:
                score = scores_dict[match_id]
                info['teamA_score'] = score['teamA']
                info['teamB_score'] = score['teamB']
                info['period'] = score['period']

            for entry in merged_list:
                if entry['tournament'] == item['tournament']:
                    tournament_exists = True
                    entry['events'].append(info)
            
            if not tournament_exists:
                logger.info(f"{item['tournament']} not in list, adding...")
                merged_list.append({'tournament' : item['tournament'], 'events' : [info]})
            else:
                logger.info(f"{entry['tournament']} already in list, adding events...")

    return merged_list

#--- Format as discord table
async def format_tournament(match):
    formatted_event = []

    # Dynamically create the header based on the number of sets
    header = [
        f"{match['period']}",
        "*",
        "1st",
        "2nd",
        "3rd"
    ]

    # Check for 4th and 5th set scores and append headers if they exist
    if len(match['teamA_score']) > 3:
        header.append("4th")
    if len(match['teamA_score']) > 4:
        header.append("5th")

    # Create rows for team A and team B, filling missing scores with "-"
    first_row = [
        f"{match['teamA']}",
        "*",
        f"{match['teamA_score'][0]}" if len(match['teamA_score']) > 0 else "-",
        f"{match['teamA_score'][1]}" if len(match['teamA_score']) > 1 else "-",
        f"{match['teamA_score'][2]}" if len(match['teamA_score']) > 2 else "-"
    ]

    if len(match['teamA_score']) > 3:
        first_row.append(f"{match['teamA_score'][3]}" if len(match['teamA_score']) > 3 else "-")
    if len(match['teamA_score']) > 4:
        first_row.append(f"{match['teamA_score'][4]}" if len(match['teamA_score']) > 4 else "-")

    second_row = [
        f"{match['teamB']}",
        "*",
        f"{match['teamB_score'][0]}" if len(match['teamB_score']) > 0 else "-",
        f"{match['teamB_score'][1]}" if len(match['teamB_score']) > 1 else "-",
        f"{match['teamB_score'][2]}" if len(match['teamB_score']) > 2 else "-"
    ]

    if len(match['teamB_score']) > 3:
        second_row.append(f"{match['teamB_score'][3]}" if len(match['teamB_score']) > 3 else "-")
    if len(match['teamB_score']) > 4:
        second_row.append(f"{match['teamB_score'][4]}" if len(match['teamB_score']) > 4 else "-")

    # Create the body of the table and format it
    body = [header, first_row, second_row]
    score_table = tabulate(body, tablefmt="simple")

    formatted_event.append(f"{match['match_name']}\n{score_table}\n")

    return formatted_event
