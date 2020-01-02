import pickle
import os.path
from calendar import monthrange
from datetime import datetime
from functools import reduce

import pandas as pd
from jinja2 import Environment, FileSystemLoader
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request


SCOPES = ['https://www.googleapis.com/auth/calendar']


def get_template_engine():
    environment = Environment(
        loader=FileSystemLoader("templates")
    )
    return environment


def get_calendar_service(namespace):

    credentials_file = os.path.join(namespace, 'authentication', 'credentials.json')
    keys_file = os.path.join(namespace, 'authentication', 'token.pickle')

    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(keys_file):
        with open(keys_file, 'rb') as token:
            creds = pickle.load(token)
        # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(keys_file, 'wb') as token:
            pickle.dump(creds, token)

    service = build('calendar', 'v3', credentials=creds)
    return service


def get_time_boundries(year, start_month, end_month):
    # Check input
    assert year.isnumeric(), "expected year to be a number"
    assert 1 <= start_month <= 12, "start_month should be between 1 and 12"
    assert 0 <= end_month <= 12, "end_month should be between 1 and 12"
    assert start_month <= end_month, "start_month should be smaller or equal to end_month"
    year = int(year)
    if not end_month:
        end_month = start_month
    # Get the datetime indicated by the input
    start_time = datetime(year=year, month=start_month, day=1)
    end_day = monthrange(year, end_month)[1]
    end_time = datetime(year=year, month=end_month, day=end_day, hour=23, minute=59, second=59)
    # 'Z' postfix indicates UTC time
    return start_time.isoformat() + "Z", end_time.isoformat() + "Z"


def get_confirmed_nonoverlap_events_frame(events):
    # Filter out any non confirmed events
    events_count = len(events)
    if not events_count:
        print("No events found")
        return
    confirmed = [event for event in events if event.get("status", None) == "confirmed"]
    confirmed_count = len(confirmed)
    if events_count > confirmed_count:
        print(f"Detected {events_count-confirmed_count} unconfirmed events")
    if not confirmed_count:
        print("Did not find any confirmed events")
        return

    # Detect overlap and exit when found
    def reduce_overlap(previous_interval, next_event):
        # Early exit when dealing with the first overlap
        if isinstance(previous_interval, dict):
            return next_event
        # Determine if there is any overlap
        next_start = next_event["start"]["dateTime"]
        next_end = next_event["end"]["dateTime"]
        next_interval = pd.Interval(pd.Timestamp(next_start), pd.Timestamp(next_end))
        # Return the event if it overlaps otherwise the interval to compare against later
        return next_interval if not previous_interval or not previous_interval.overlaps(next_interval) else next_event
    result = reduce(reduce_overlap, confirmed, None)
    if isinstance(result, dict):
        print(f"Found an overlapping event {result['summary']} starting on {result['start']['dateTime']}")
        return

    # Return DataFrame for all valid events
    data = [
        {
            "activity": event["summary"],
            "day": pd.Timestamp(event["start"]["dateTime"]).strftime("%d-%m-%Y"),
            "start": pd.Timestamp(event["start"]["dateTime"]).strftime("%H:%M"),
            "end": pd.Timestamp(event["end"]["dateTime"]).strftime("%H:%M"),
            "duration": pd.Interval(
                pd.Timestamp(event["start"]["dateTime"]),
                pd.Timestamp(event["end"]["dateTime"])
            ).length
        }
        for event in confirmed
    ]
    return pd.DataFrame(data=data)
