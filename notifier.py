import os
import pytz
import discord
import asyncio
import aiohttp
from db import db
from loguru import logger
from dotenv import load_dotenv
from utils import get_current_ny_time
from datetime import datetime, timedelta

load_dotenv()

current_branch = "PROD"

def get_token():
    if current_branch == "DEV":
        DISCORD_API = os.getenv("DISCORD_WEBHOOK_DEV")
    elif current_branch == "PROD":
        DISCORD_API = os.getenv("DISCORD_WEBHOOK_PROD")
    return DISCORD_API

WEBHOOK_URL = get_token()

async def glitch_notifier(glitches, match_name, current_set, site, score_site):
    output = "\n".join(glitches)
    text = (
        f"👾 **Glitch found in {site}!**\n\n"
        f"**Match:** {match_name}\n"
        f"**Current Set on {score_site}:** {current_set}\n"
        f"**Line(s):** \n"
        f"{output}\n\n"
        f"**Time:** {get_current_ny_time()}"
    )
    async with aiohttp.ClientSession() as session:
        webhook = discord.Webhook.from_url(WEBHOOK_URL, session=session)
        message = await webhook.send(text, username='Odds Bot', wait=True)
        print(message.id)

