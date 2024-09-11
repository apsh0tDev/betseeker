import pytz
from datetime import datetime

def get_current_ny_time():
    # Define New York timezone
    ny_tz = pytz.timezone('America/New_York')
    ny_time = datetime.now(ny_tz)
    return ny_time.strftime('%Y-%m-%d %I:%M %p')

def format_datetime(input_datetime_str):
    input_datetime = datetime.fromisoformat(input_datetime_str.replace('Z', '+00:00'))
    ny_timezone = pytz.timezone('America/New_York')
    input_datetime = input_datetime.astimezone(ny_timezone)
    current_datetime = datetime.now(ny_timezone)
    day_difference = (input_datetime.date() - current_datetime.date()).days
    if day_difference == 0:
        day_str = "Today"
    elif day_difference == 1:
        day_str = "Tomorrow"
    else:
        day_str = input_datetime.strftime("%A")
    time_str = input_datetime.strftime("%I:%M %p")

    return f"{day_str} - {time_str}"
