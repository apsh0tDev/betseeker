from enum import Enum
import asyncio
from typing import List
from db import db
from scrapingant_client import Response, ScrapingAntClient

class Types(Enum):
    GENERAL = "general_request"
    ASYNC_GENERAL = "general_request_async"
    MARKDOWN = "markdown_request"
    ASYNC_MARKDOWN = "markdown_request_async"

async def add_token (token:str, count:int=10_000):
    res = db.table("tokens").insert({
        "token": token,
        "count": count
    }).execute()

    return res

async def get_token (update_count=0):
    table = db.table("tokens")
    tokens = table.select("*").execute().data
    if not tokens: return

    def key(x):
        return x["id"]

    tokens.sort(key=key)
        
    token = tokens[0]

    if token["count"] <= 0:
        table.delete().eq("id", token["id"]).execute()
        token = tokens[1]

    if token["count"] >= 1:
        table.update({ "count": token["count"] + update_count }).eq("id", token["id"]).execute()

    return token

class Ant:
    def __init__(self):
        self.count = None
        self.token = None
        self.client = None

    @classmethod
    async def create(cls):
        self = cls()
        t = await get_token()
        self.count = t["count"]
        self.token = t["token"]
        self.client = ScrapingAntClient(token=t["token"])
        return self

    async def reset_token(self):
        t = await get_token()
        self.count = t["count"]
        self.token = t["token"]
        self.client = ScrapingAntClient(token=t["token"])

    async def update_count(self, new_count=None):
        if not new_count:
            new_count = self.count

        self.count = new_count

        r = db.table("tokens").update({
            "count": new_count
        }).eq("token", self.token).execute()

        if self.count <= 0:
            await self.reset_token()

    async def request(self, type:str, url:str, is_group=False, **params):
        types = {
            "general_request": self.client.general_request,
            "general_request_async": self.client.general_request_async,
            "markdown_request": self.client.markdown_request,
            "markdown_request_async": self.client.markdown_request_async
        }
        if not type in types:
            type = "general_request"
            print("request type not recognized, switching to general_request")

        func = types[type]
        if type.endswith("async"):
            result:Response = await func(url, **params)
        else:
            result:Response = func(url, **params)

        if not is_group:
            await self.update_count(self.count - 1)

        return result
        
    async def requests_exec(self, info_list:List[dict], common:dict=None):
        tasks = []
        request = self.request

        if len(info_list) > self.count:
            info_list = info_list[:self.count]

        for i in range(len(info_list)):
            if common:
                info_list[i].update(common)
            
        res:List[Response] = await asyncio.gather(*[
            request(**info) for info in info_list
        ])

        await self.update_count(self.count - len(tasks))

        return res