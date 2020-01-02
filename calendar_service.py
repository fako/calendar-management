import pickle
import os.path
from calendar import monthrange
from datetime import datetime

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request


SCOPES = ['https://www.googleapis.com/auth/calendar']


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
    assert year.isnumeric(), "expected year to be a number"
    assert 1 <= start_month <= 12, "start_month should be between 1 and 12"
    assert 1 <= end_month <= 12, "end_month should be between 1 and 12"
    assert start_month <= end_month, "start_month should be smaller or equal to end_month"
    year = int(year)
    start_time = datetime(year=year, month=start_month, day=1)
    end_day = monthrange(year, end_month)[1]
    end_time = datetime(year=year, month=end_month, day=end_day)
    # 'Z' postfix indicates UTC time
    return start_time.isoformat() + "Z", end_time.isoformat() + "Z"
