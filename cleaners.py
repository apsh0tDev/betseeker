from db import db
from loguru import logger

async def clean(data, table, source):
    print(f"Run cleaners for {table}🧹 - {source}")
    table_name = table
    table = db.table(table).select("*").eq("source", source).execute()
    ids = [int(item['match_id']) for item in table.data]
    for record_id in ids:
        if record_id not in data:
            logger.info(f"Deleting {record_id} from {table_name} table")
            db.table(table_name).delete().eq("match_id", record_id).execute()
    print(f"Done cleaning {table_name}🧹 - {source}")

async def clean_schedule(data):
    print(f"Run cleaners for schedule")
    table = db.table("schedule").select("*").execute()
    ids = [int(item['match_id']) for item in table.data]

    for record_id in ids:
        if record_id not in data:
            logger.info(f"Deleting {record_id} from schedule table")
            db.table("schedule").delete().eq("match_id", record_id).execute()
    print(f"Done cleaning schedule 🧹")