from invoke import task

from calendar_service import get_calendar_service, get_time_boundries, get_confirmed_nonoverlap_events_frame


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
        print(f'No events found between {year}-{start_month} and {year}-{end_month}')
        return
    frame = get_confirmed_nonoverlap_events_frame(events)
    if frame is None:
        return
    total_time = frame["duration"].sum().total_seconds()
    total_hours = total_time / 60 / 60
    print(f"Total hours: {total_hours}")
    print(frame.to_html())
