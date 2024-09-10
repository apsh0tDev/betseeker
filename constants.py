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