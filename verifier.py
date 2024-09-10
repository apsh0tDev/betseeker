from loguru import logger

async def verifier(value):
    if value != None and 'solution' in value and 'verified' in value['solution'] and value['solution']['verified'] == True and 'response' in value['solution']:
        if "<title>Just a moment...</title>" not in value['solution']['response'] and "Request blocked." not in value['solution']['response'] and "Sorry, you have been blocked" not in value['solution']['response']:
            return True
        else:
            logger.error("CLOUDFARE BLOCK.")
            return False
    else:
        logger.error(value)
        return False
    
async def verifier_alt(value):
    if value != None and "Request blocked." not in value and "Just a moment..." not in value and "Sorry, you have been blocked" not in value:
        return True
    return False