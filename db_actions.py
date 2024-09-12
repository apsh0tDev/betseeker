from db import db

async def exists(table, to_match):
    response = db.table(table).select("*").match(to_match).execute()
    return True if len(response.data) > 0 else False

async def update(table, info, to_match):
    response = db.table(table).update(info).match(to_match).execute()
    return response

async def upload(table, info):
    response = db.table(table).insert(info).execute()
    return response

async def db_actions(to_match, to_update, info, table):
    value_exists = await exists(to_match=to_match, table=table)
    if value_exists:
        response = await update(table=table, to_match=to_match, info=to_update)
        print(response)
    else:
        response = await upload(table=table, info=info)
        print(response)
