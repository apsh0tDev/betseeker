import bs4
import json
import discord
import asyncio
import pytz
from db import db
from rich import print
from loguru import logger
from utils import format_datetime
from constants import Site, fanduel_url
from connection import scrape_by_site
from verifier import verifier_alt
from datetime import datetime, timezone

#------ Schedule function for bot - Schedule is based on 365scores
async def get_schedule():
    result = db.table("schedule").select("*").execute()
    response = await format_schedule(result.data)
    return response

async def format_schedule(data):
    logger.info("Formatting schedule for discord")
    if len(data) > 0:
        try:
            fields_added = 0
            embeds = []
            current_embed = discord.Embed(title="Schedule 📅")

            for event in data:
                event_name = event.get('match_name', '')
                event_tournament = event.get('tournament', '')
                event_date = format_datetime(event.get('date', ''))
                if isinstance(event_name, str) and event_name.strip() != '' and isinstance(event_tournament, str) and event_tournament.strip() != '' and isinstance(event_date, str) and event_date.strip() != '':
                    field_value = f"{event_tournament} - {event_date}"
                    if len(current_embed) + len(event_name) + len(field_value) <= 6000 and fields_added < 25:
                            current_embed.add_field(name=event_name, value=field_value, inline=False)
                            fields_added += 1
                    else:
                            embeds.append(current_embed)
                            current_embed = discord.Embed(title="Schedule 📅")
                            fields_added = 0

            embeds.append(current_embed)
            for index, embed in enumerate(embeds):
                if index < 10:  # Limit to 10 embeds per message
                    return embed
                else:
                    logger.warning("Maximum number of embeds per message reached")
                    break 
        except Exception as e:
            logger.error(f"There was an Error formatting the message: {e}")       
    else:
        return "No events scheduled."


#------ Individual schedules for each sportsbook
async def get_live_matches(source):
    table = db.table("matches_list").select("*").eq("source", source).execute()
    if len(table.data) > 0:
         return
    else:
         match source:
              case "FANDUEL":
                   await get_fanduel_schedule()
                   

async def get_fanduel_schedule():
    response = await scrape_by_site(fanduel_url, Site.FANDUEL.value, True)
    if response != None and response != '':
         is_valid = await verifier_alt(response)
         if is_valid:
                scheduled_dates = []
                soup = bs4.BeautifulSoup(response, 'html.parser')
                pre = soup.find("pre")
                load = json.loads(pre.text)
                if 'attachments' in load and 'markets' in load['attachments']:
                    markets = load['attachments']['markets']
                    market_keys = [key for key in markets]
                    for key in market_keys:
                        if 'inPlay' in markets[key] and markets[key]['inPlay'] == False:
                             scheduled_dates.append(markets[key]['marketTime'])
                now_utc = datetime.now(timezone.utc)
                parsed_timestamps = [
                    {
                        "original": ts,
                        "datetime": datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
                    }
                    for ts in scheduled_dates
                ]
                sorted_timestamps = sorted(parsed_timestamps, key=lambda x: abs((x["datetime"] - now_utc).total_seconds()))
                ny_tz = pytz.timezone("America/New_York")
                closest_datetime = sorted_timestamps[0]["datetime"]
                closest_ny_time = closest_datetime.astimezone(ny_tz)

                await update_fanduel_time_in_file("schedule_times.txt", closest_ny_time, Site.FANDUEL.value)


#REWRITE TIME
async def update_fanduel_time_in_file(file_path, closest_ny_time, site):
    # Read the contents of the file
    with open(file_path, 'r') as file:
        lines = file.readlines()

    # Iterate over the lines and find the "FANDUEL:" line
    for i, line in enumerate(lines):
        if line.startswith(f"{site}:"):
            # Update the line with the closest New York time
            lines[i] = f"{site}: {closest_ny_time.strftime('%Y-%m-%d %H:%M:%S %Z')}\n"
            break  # No need to check further once we find the line

    # Write the updated content back to the file
    with open(file_path, 'w') as file:
        file.writelines(lines)
                
                
                             


if __name__ == "__main__":
     asyncio.run(get_fanduel_schedule())
