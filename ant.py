from enum import Enum
import asyncio
from random import randint
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

async def get_token (update_count=0, token_id=None):
    table = db.table("tokens")
    if token_id:
        tokens = table.select("*").eq("id", token_id).execute().data
        
    else:
        tokens = table.select("*").execute().data
        def key(x):
            return x["id"]

        tokens.sort(key=key)

    if not tokens: return

    token = tokens[0]

    if token["count"] <= 0:
        table.delete().eq("id", token["id"]).execute()
        if token_id:
            return
        token = tokens[1]

    if token["count"] >= 1:
        table.update({ "count": token["count"] + update_count }).eq("id", token["id"]).execute()

    return token

class Ant:
    def __init__(self):
        self.count = None
        self.token = None
        self.token_id = None
        self.client = None

    @classmethod
    async def create(cls, token:dict=None):
        self = cls()
        t = token if token else await get_token()
        self.count = t["count"]
        self.token = t["token"]
        self.token_id = t["id"]
        self.client = ScrapingAntClient(token=t["token"])
        return self

    async def reset_token(self):
        t = await get_token()
        self.count = t["count"]
        self.token = t["token"]
        self.token_id = t["id"]
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

    async def request(self, type:str, url:str, **params):
        print("Accessing " + url + "...")
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

        await self.update_count(self.count - 1)

        return result
    
def mix_el (array, index1, index2):
    new_arr = [item for item in array]
    new_arr[index2] = array[index1]
    new_arr[index1] = array[index2]

    return new_arr
    
class Nest:
    def __init__(self):
        self.tokens:List[dict] = []

    @classmethod
    async def create(cls, ant_limit=5):
        self = cls()
        all_tokens = db.table("tokens").select("*").limit(ant_limit).execute().data

        for i in range(len(all_tokens)):
            r1 = randint(0, len(all_tokens) - 1)
            r2 = randint(0, len(all_tokens) - 1)
            all_tokens = mix_el(all_tokens, r1, r2)

        self.tokens = all_tokens

        return self
    
    async def check_ants(self, ants:List[Ant]=None):
        if not ants:
            all_tokens = db.table("tokens").select("*").limit(len(self.tokens)).execute().data
            for i in range(len(all_tokens)):
                r1 = randint(0, len(all_tokens) - 1)
                r2 = randint(0, len(all_tokens) - 1)
                all_tokens = mix_el(all_tokens, r1, r2)
        else:
            all_tokens = [ { "token": ant.token, "count":ant.count, "id":ant.token_id } for ant in ants ]

        self.tokens = all_tokens

    async def requests(self, info_list:List[dict], common:dict=None):
        tasks = []

        if len(info_list) > len(self.tokens):
            info_list = info_list[:len(self.tokens)]

        needs_check = False

        ants:List[Ant] = []

        for i in range(len(info_list)):
            info, ant = [info_list[i], await Ant.create(self.tokens[i])]
            if common:
                info.update(common)
            if ant.count <= 1:
                needs_check = True
            tasks.append(asyncio.create_task(ant.request(**info)))

            ants.append(ant)

        res = await asyncio.gather(*tasks)

        check_arg = None if needs_check else ants

        await self.check_ants(check_arg)
        
        return res
