import os
from invoke import task
from math import floor

from pandas.io.formats.format import Timedelta64Formatter

from calendar_service import (get_calendar_service, get_time_boundries, get_confirmed_nonoverlap_events_frame,
                              get_template_engine)


CUSTOMER_TO_CALENDAR_ID = {
    "surf": "fakoberkers.nl_2md1qlaos828miq6fiasqhj2hs@group.calendar.google.com",
    "bns": "c_19of6juc7hqv1mq0u124909u9s@group.calendar.google.com",
    "nppo": "c_phh2uirvu4n21mgfv70e3tqjg4@group.calendar.google.com"
}


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
