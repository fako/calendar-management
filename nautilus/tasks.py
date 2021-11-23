import os
from datetime import date
from urllib.parse import unquote
from getpass import getpass
from invoke import task, Exit
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

from calendar_service import get_calendar_service, get_template_engine


CALENDARS = {
    "vve-mededelingen": {
        "zaal": "opmk262p9m2m6dfecr9mh3k3o0@group.calendar.google.com",
        "expo": "j84v91s3kmrs8ar513smdqvlq8@group.calendar.google.com",
        "kamer": "qjfvat6t7kei30788gehgstbt0@group.calendar.google.com"
    },
    "gebouw": {
        "gebouw": "ph5kjn373elgur93u3i50m4urc@group.calendar.google.com"
    }
}
GROUPS = [
    "communicatie",
    "financien",
    "gebouw",
    "kascommissie",
    "logeerkamer",
    "programmering",
    "publieke-werken",
    "tuin",
    "vluchtelingenkamer",
    "vve-bestuur",
    "zaal"
]


def login_mailman(list_url, mailman_password):
    session = requests.Session()
    response = session.post(list_url, data={"adminpw": mailman_password})
    if response.status_code != 200:
        raise Exit("Could not login to mailman. Is the password correct?")
    return session


def fetch_members(session, list_url):
    response = session.get(f"{list_url}/members")
    if response.status_code != 200:
        raise Exit("Could not fetch mailman members.")
    soup = BeautifulSoup(response.content, features="html.parser")
    all_members = set()
    for input in soup.find_all("input", attrs={"name": "user"}):
        all_members.add(unquote(input["value"]))
    return all_members


@task()
def sync_calendar_permissions(ctx, group="vve-mededelingen"):

    list_url = f"http://lists.nautilus-amsterdam.nl/mailman/admin/{group}"
    mailman_password = getpass()
    session = login_mailman(list_url, mailman_password)
    print("Login successful")
    all_members = fetch_members(session, list_url)

    # Figure out which e-mails are missing access for each calendar
    service = get_calendar_service("nautilus")
    calendars = CALENDARS[group]
    for name, calendar_id in calendars.items():
        print("Subscribing members to:", name)
        acl_list_result = service.acl().list(calendarId=calendar_id).execute()
        calendar_members = set()
        for item in acl_list_result.get("items", []):
            calendar_members.add(item["scope"]["value"])
        missing_members = all_members - calendar_members
        for member in tqdm(missing_members):
            acl_insert = {
                "id": f"user:{member}",
                "role": "reader",
                "scope": {
                    "type": "user",
                    "value": member
                }
            }
            service.acl().insert(calendarId=calendar_id, body=acl_insert, sendNotifications=True).execute()


@task()
def generate_groups_overview(ctx):
    groups = []
    mailman_password = getpass()
    for group_code in GROUPS:
        print(f"Processing: {group_code}")
        list_url = f"http://lists.nautilus-amsterdam.nl/mailman/admin/{group_code}"
        session = login_mailman(list_url, mailman_password)
        members = fetch_members(session, list_url)
        group = {
            "code": group_code,
            "name": group_code.replace("-", " ").capitalize(),
            "email": f"{group_code}@nautilus-amsterdam.nl",
            "members": members
        }
        groups.append(group)
    engine = get_template_engine()
    overview_file = os.path.join("nautilus", "overviews", f"werkgroepen-{date.today()}.html")
    overview = engine.get_template("werkgroepen.html")
    with open(overview_file, "w") as fd:
        fd.write(overview.render(groups=groups))
