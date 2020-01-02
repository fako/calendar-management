import datetime
from invoke import task

from calendar_service import get_calendar_service, get_time_boundries


@task
def list_events(ctx, username, year, start_month=1, end_month=12):
    time_start, time_end = get_time_boundries(year, start_month, end_month)
    calendar_id = f"{username}@goodfashionfriend.com"
    service = get_calendar_service("future_fashion")
    events_result = service.events() \
        .list(calendarId=calendar_id, timeMin=time_start, timeMax=time_end, singleEvents=True, orderBy='startTime')\
        .execute()
    events = events_result.get('items', [])
    if not events:
        print('No upcoming events found.')
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        print(start, event['summary'])
