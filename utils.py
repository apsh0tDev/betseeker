import pytz
from datetime import datetime

def get_current_ny_time():
    # Define New York timezone
    ny_tz = pytz.timezone('America/New_York')
    ny_time = datetime.now(ny_tz)
    return ny_time.strftime('%Y-%m-%d %I:%M %p')