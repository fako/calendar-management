import os
from invoke import task
from math import floor

from pandas.io.formats.format import Timedelta64Formatter

from calendar_service import (get_calendar_service, get_time_boundries, get_confirmed_nonoverlap_events_frame,
                              get_template_engine)


@task
def report_events(ctx, username, year, start_month=1, end_month=12, report=False):
    # Get and parse events
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
    # Get basic aggregations
    total_time = frame["duration"].sum().total_seconds()
    total_hours = total_time / 60 / 60
    residu_hours = total_hours % 8
    # Write report
    if report:
        # Get template engine and basic variables
        engine = get_template_engine()
        if start_month != end_month:
            file_name = f"{username}_{year}-{start_month}_tm_{year}-{end_month}"
            title = f"Uren registratie {calendar_id} voor {year}-{start_month} t/m {year}-{end_month}"
        else:
            file_name = f"{username}_{year}-{start_month}"
            title = f"Uren registratie {calendar_id} voor {year}-{start_month}"
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
        report_file = os.path.join("future_fashion", "reports", f"{file_name}.html")
        report = engine.get_template("report.html")
        with open(report_file, "w") as fd:
            fd.write(report.render(title=title, table=frame.to_html(index=False), total_hours=total_hours,
                                   residu_hours=residu_hours))
        # Create PDF
        with ctx.cd(os.path.join("future_fashion", "reports")):
            ctx.run(f"wkhtmltopdf {file_name}.html {file_name}.pdf")
    # CLI output
    print(f"Total hours: {total_hours}")
    print(f"Total time: {floor(total_hours/8)} days and {residu_hours} hours")
