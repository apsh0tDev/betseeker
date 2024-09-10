from enum import Enum

class Site(Enum):
    SOFASCORE = "SOFASCORE"
    SCORES365 = "365SCORES"
    DRAFTKINGS = "DRAFTKINGS"
    FANDUEL = "FANDUEL"
    BETMGM = "BETMGM"
    POINTSBET = "POINTSBET"


#===== Scores 
#Sofascore
sofascore_url = "https://www.sofascore.com/api/v1/sport/{sport_name}/events/live"
#365Scores
scores365_url = "https://webws.365scores.com/web/games/allscores/?appTypeId=5&langId=9&timezoneName=America/NewYork&userCountryId=18&sports={sportId}&startDate={startDate}&endDate={endDate}&showOdds=true&onlyLiveGames=false&withTop=true"

#===== Sportsbooks
#FaDuel
fanduel_live_url = "https://sbapi.ny.sportsbook.fanduel.com/api/in-play?timezone=America%2FNew_York&eventTypeId={eventTypeID}&includeTabs=false&_ak=FhMFpcPWXMeyZxOx"
fanduel_url = f"https://sbapi.ny.sportsbook.fanduel.com/api/content-managed-page?page=SPORT&eventTypeId=2&_ak=FhMFpcPWXMeyZxOx&timezone=America%2FNew_York"
fanduel_event_url = "https://sbapi.ny.sportsbook.fanduel.com/api/event-page?_ak=FhMFpcPWXMeyZxOx&eventId={id}&tab={tab}&useCombinedTouchdownsVirtualMarket=true&usePulse=true&useQuickBets=true"


