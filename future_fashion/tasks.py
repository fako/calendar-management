import datetime
from invoke import task

from calendar_service import get_calendar_service


@task
def list_events(ctx, username):
    calendar_id = f"{username}@goodfashionfriend.com"
    now = datetime.datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
    service = get_calendar_service("future_fashion")
    events_result = service.events().list(calendarId=calendar_id, timeMin=now,
                                          maxResults=10, singleEvents=True,
                                          orderBy='startTime').execute()
    events = events_result.get('items', [])
    if not events:
        print('No upcoming events found.')
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        print(start, event['summary'])
