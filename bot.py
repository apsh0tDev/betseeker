import os
import discord
import textwrap
from db import db
from thefuzz import fuzz
from loguru import logger
from constants import Site
from tabulate import tabulate
from dotenv import load_dotenv
from discord.ext import commands
from glitch_catcher import format_glitches
from live import get_live_matches
from schedule import get_schedule
from arbs import format_arbitrages

#---- Init
load_dotenv()
current_branch = "PROD"
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

def get_token():
    DISCORD_API = ''
    if current_branch == "DEV":
        DISCORD_API = os.getenv("TOKEN_DEV")
    elif current_branch == "PROD":
        DISCORD_API = os.getenv("TOKEN_PROD")
    return DISCORD_API

logger.add("discord_errors.log", filter=lambda record:"discord_error" in record["extra"])

#======= Bot Events =========

@bot.event
async def on_ready():
    print("Bot ready to go!")

@bot.event
async def on_command_error(ctx: commands.Context, error):
    try:
            # Log all unhandled errors
            logger.bind(discord_error=True).error(f'Ignoring exception in command {ctx.command}: {type(error).__name__}: {error}')
            await ctx.send("An error occurred. Please try again later.")
    except Exception as e:
        # Catch any exception that occurs within the error handler itself
        logger.bind(discord_error=True).error(f'Exception in error handler: {type(e).__name__}: {e}')
        

#==== End of Bot Events =====

#====== Bot Commands ========
@bot.command()
async def commands(ctx):
    commands_message = f"""
                        🤖 **Commands:**
                        `!live`: Displays a full list of today's live matches and current scores - Default 365scores
                        `!live [sofascore/365scores]`: Displays a full list of today's live matches and current scores from the specified source (default is 365scores)
                        `!schedule`: Displays a list of scheduled events
                        `!sportsbooks` : Displays a list of available sportsbooks and their current availability
                        `!logs [arbitrages/glitches]`: Retrieves the log files for arbitrages or glitches based on the provided argument
                        """
    await ctx.send(commands_message)

@bot.command()
async def live(ctx, source = ''):
    if source.lower() == "sofascore":
        res = await get_live_matches(Site.SOFASCORE.value)
        # Add your logic for SofaScore here
    elif source.lower() == "365scores":
        res = await get_live_matches(Site.SCORES365.value)
        # Add your logic for 365Scores here
    else:
        res = await get_live_matches(Site.SCORES365.value)

    if res is not None:
        if isinstance(res, list):
            for embed in res:
                await ctx.send(embed=embed)
        else:
            await ctx.send(embed=res)
    else:
        await ctx.send("There are no live matches at the moment.")

@bot.command()
async def schedule(ctx):
    message = await get_schedule()
    if isinstance(message, str):
        await ctx.send(message)
    else:
        await ctx.send(embed=message)

@bot.command()
async def sportsbooks(ctx):
    res = db.table("sportsbooks").select("*").execute()
    if len(res.data) > 0:
        header = ["Sportsbook", "Is available", "Availability Avg"]
        body = [header]  # Start with the header
        # Add each sportsbook and its availability as a new row

                # Define ANSI color codes for Available and Not Available
        available_format = "\u001b[1;40;32m Available \u001b[0m"
        not_available_format = "\u001b[1;40;31m Not Available \u001b[0m"  # Bright red text
        
        for item in res.data:
            total_count = item['available_sum'] + item['not_available_sum']
            avg = round((item['available_sum'] / total_count) * 100)
            row = [item['name'], available_format if item['available'] == True else not_available_format, f"\u001b[1;40;32m {avg}% \u001b[0m" if avg > 60 else f"\u001b[1;40;31m {avg}% \u001b[0m"]
            body.append(row)
        table = tabulate(body, headers="firstrow", tablefmt="simple")
        message = f"```ansi\n{table}\n```"
        message = textwrap.dedent(message)
        await ctx.send(message)
        await ctx.send("For real-time information, please visit [this link](https://apsh0tdev.github.io/spAvailability/)")

@bot.command()
async def logs(ctx, file = ''):
    if file == '':
        await ctx.send("It seems like you didn't specify any log file! Please type `arbitrages` or `glitches` to get the corresponding logs.")
    else:
        fuzz_ratio_arb = fuzz.ratio("arbitrages", file)
        if fuzz_ratio_arb >= 85:
            log_file = "arbitrages.log"
            await ctx.send(file=discord.File(log_file))

        fuzz_ratio_glitch = fuzz.ratio("glitches", file)
        if fuzz_ratio_glitch >= 85:
            log_file = "glitches.log"
            await ctx.send(file=discord.File(log_file))

        if fuzz_ratio_glitch < 80 and fuzz_ratio_arb < 80:
            await ctx.send(f"❓ I'm not sure what `{file}` refers to. Try `arbitrages` or `glitches` for the correct logs.")

@bot.command()
async def arbitrages(ctx):
    live = db.table("matches_list").select("*").execute()
    if len(live.data) > 0:
        arbitrages = db.table("arbitrages").select("*").execute()
        if len(arbitrages.data) > 0:
            table = await format_arbitrages(arbitrages.data)
            message = f"```ansi\n{table}\n```"
            await ctx.send(message)
        else:
            await ctx.send("No arbitrages found.")
    else:
        await ctx.send("No arbitrages found.")

@bot.command()
async def glitches(ctx):
    glitches = db.table("glitches").select("*").execute()
    if len(glitches.data) > 0:
        table = await format_glitches(glitches.data)
        message = f"```ansi\n{table}\n```"
        await ctx.send(message)
    else:
            await ctx.send("No glitches found.")
 

#=== End of Bot Commands ====

if __name__ == "__main__":
    bot.run(get_token())
