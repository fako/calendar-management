import os
from invoke import task
from math import floor
from datetime import datetime, timedelta

from pandas.io.formats.format import Timedelta64Formatter

from calendar_service import (get_calendar_service, get_time_boundries, get_confirmed_nonoverlap_events_frame,
                              get_template_engine)


CUSTOMER_TO_CALENDAR_ID = {
    "fako": "email@fakoberkers.nl",
    "edusources": "fakoberkers.nl_2md1qlaos828miq6fiasqhj2hs@group.calendar.google.com",
    "bns": "c_19of6juc7hqv1mq0u124909u9s@group.calendar.google.com",
    "nppo": "c_phh2uirvu4n21mgfv70e3tqjg4@group.calendar.google.com",
    "datascope": "fakoberkers.nl_qcr2r6ne4b8fm3pnj7u5f42vhk@group.calendar.google.com",
    "publinova": "c_dhvua3pb4el5jkpse90a275oek@group.calendar.google.com",
    "autometa": "c_ace4691e4f3ce66ccd1441b3a78c81f7868c59026578a9b8f658153c3304498b@group.calendar.google.com",
    "toekomst_atelier": "c_5cc955c247fce047fa28661b1e2d0c10498465e995c77bec723f26882ea15171@group.calendar.google.com",
}
WEEK_DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


@task
def report_events(ctx, customer, year, start_month=1, end_month=12, until=0, to_file=False):
    # Get and parse events
    until = until or None
    time_start, time_end = get_time_boundries(year, start_month, end_month, end_day=until)
    calendar_id = CUSTOMER_TO_CALENDAR_ID[customer]
    service = get_calendar_service("datascope")
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
    # Get basic aggregations
    total_time = frame["duration"].sum().total_seconds()
    total_hours = total_time / 60 / 60
    # Write report
    if to_file:
        # Get template engine and basic variables
        engine = get_template_engine()
        start_month_text = str(start_month).zfill(2)
        end_month_text = str(end_month).zfill(2)
        if start_month != end_month:
            file_name = f"{customer}_{year}-{start_month_text}_tm_{year}-{end_month_text}"
            title = f"Uren registratie {customer} voor {year}-{start_month_text} t/m {year}-{end_month_text}"
        else:
            file_name = f"{customer}_{year}-{start_month_text}"
            title = f"Uren registratie {customer} voor {year}-{start_month_text}"
        # Format time delta's without seconds
        frame["duration"] = Timedelta64Formatter(frame["duration"]).get_result()
        frame["duration"] = frame["duration"].apply(lambda dur: dur[:-3])
        # Translate the output
        frame = frame.rename(axis="columns", mapper={
            "activity": "activiteit",
            "day": "dag",
            "end": "einde",
            "duration": "duur (uren:minuten)"
        })
        # Write to HTML file
        report_file = os.path.join("datascope", "reports", f"{file_name}.html")
        report = engine.get_template("report.html")
        with open(report_file, "w") as fd:
            fd.write(report.render(title=title, table=frame.to_html(index=False), total_hours=total_hours))
        # Create PDF
        with ctx.cd(os.path.join("datascope", "reports")):
            ctx.run(f"wkhtmltopdf {file_name}.html {file_name}.pdf")
    # CLI output
    print(f"Total hours: {total_hours}")
    print(f"Total time: {floor(total_hours/8)} days and {total_hours%8} hours")
    return total_hours


@task
def report_week(ctx, customer, year, week):
    time_start = datetime.strptime(f'{year}-W{int(week)}-1', "%Y-W%W-%w")
    time_end = time_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
    time_start = time_start.isoformat() + "Z"
    time_end = time_end.isoformat() + "Z"
    calendar_id = CUSTOMER_TO_CALENDAR_ID[customer]
    service = get_calendar_service("datascope")
    events_result = service.events() \
        .list(calendarId=calendar_id, timeMin=time_start, timeMax=time_end, singleEvents=True, orderBy='startTime') \
        .execute()
    events = events_result.get('items', [])
    if not events:
        print(f'No events found for week {week} in {year}')
        return 0
    frame = get_confirmed_nonoverlap_events_frame(events)
    if frame is None:
        return 0
    frame["weekday"] = frame["day"].apply(lambda day: datetime.strptime(day, "%d-%m-%Y").strftime("%a"))
    durations = frame.groupby(["weekday"])["duration"].sum()
    for week_day in WEEK_DAYS:
        if week_day not in durations:
            continue
        print(week_day, "\t", durations[week_day].total_seconds() / 60 / 60)
    total_time = durations.sum().total_seconds()
    total_hours = total_time / 60 / 60
    print()
    print(f"Total hours: {total_hours}")
    print(f"Total time: {floor(total_hours/8)} days and {total_hours%8} hours")
    return total_hours


@task(iterable="weeks")
def report_weeks(ctx, customer, year, weeks):
    total_hours = 0
    for week in weeks:
        print()
        print(f"Hours for week {week}")
        total_hours += report_week(ctx, customer, year, week)
    print()
    print(f"Total hours: {total_hours}")
    print(f"Total time: {floor(total_hours/8)} days and {total_hours%8} hours")


@task(iterable="customers")
def report_quarter(ctx, customers, year, quarter):
    start_month = (int(quarter) - 1) * 3 + 1
    end_month = start_month + 2
    hours = 0
    for customer in customers:
        customer_hours = report_events(ctx, customer, year, start_month, end_month, to_file=True)
        if customer_hours is not None:
            hours += customer_hours
    print(f"Total hours this quarter: {hours}")
    print(f"Quarter norm is: {1225/4}")
