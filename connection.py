import os
import json
import aiohttp
import requests
from rich import print
from loguru import logger
from dotenv import load_dotenv
from dev_notifier import notification
from scrapingant_client import ScrapingAntClient

load_dotenv()
key = os.getenv("SCRAPPEY_KEY")
headers = { 'Content-Type' : 'application/json' }
scrappey = f"https://publisher.scrappey.com/api/v1?key={key}"

# For simple scrapes of websites that are not too strict, it can receive a "data" object, eg: 
# data = {
#         'cmd' : 'request.get',
#         'url' : 'http://exampleurl.com',
#         'requestType' : 'request',
#     }
# if the website needs a proxy but the security is not too strict, then it needs this parameter: 'proxyCountry' : 'UnitedStates'
# after 'requestType'. Websites that don't need a proxy at all: 365scores and BetMGM

async def scrape(data, site):
    logger.info(f"Scraping from {site}")
    async with aiohttp.ClientSession() as session:
        async with session.post(scrappey, headers=headers, json=data) as response:
            if response.status == 200:
                text = await response.text(encoding="ISO-8859-1", errors="ignore")  # Ignore decoding errors
                return json.loads(text)
            else:
                print(response)
                logger.error("ERROR")
                return None

# For complex scrapes of websites that need a proxy and headless browser
# you can remove 'requestType' : 'request' from the data object but it would take longer to respond.
# A better option is to use burner Scraping Ant accounts with rotating keys and use the function below

async def get_token(site):
    name = site.upper()
    match name:
        case "DRAFTKINGS":
            key = os.getenv("DRAFTKINGS_SAT")
        case "FANDUEL":
            #key = "3694aae01a234cdabae7356992e80919"
            key = "2b1586e4cdc64bf89f7da099443c5b7d"
            
    return key

async def scrape_by_site(url, site, headless):
    logger.info(f"Scraping from {site} - Using Alt")
    token = await get_token(site)
    client = ScrapingAntClient(token=token)
    try:
        result = client.general_request(url, proxy_country='US')
        if result.status_code == 200:
            return result.content
        else:
            print(result.content)
            await notification(f"{site} // {result.content}")
            return None 
    except Exception as e:
        print(e)
        await notification(f"{site} // {e}")
        return None


        
