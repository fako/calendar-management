import os
import re
from invoke import task
from math import floor

from calendar_service import (get_calendar_service, get_time_boundries, get_confirmed_nonoverlap_events_frame,
                              get_template_engine)


activity_category_pattern = re.compile("^\s*\[\s*(\w+)\s*\]")


def get_activity_category(activity):
    match = activity_category_pattern.match(activity)
    if not match:
        return "gff"
    category = match.group(1)
    if category in ["Other", "other"]:
        category = "oth"
    return category.lower()


@task
def report_events(ctx, username, year, start_month=1, end_month=12, until=0, to_file=False):
    # Get and parse events
    until = until or None
    time_start, time_end = get_time_boundries(year, start_month, end_month, end_day=until)
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
    frame["category"] = frame["activity"].apply(get_activity_category)
    # Write report
    if to_file:
        # Get template engine and basic variables
        engine = get_template_engine()
        start_month_text = str(start_month).zfill(2)
        end_month_text = str(end_month).zfill(2)
        if start_month != end_month:
            file_name = f"{username}_{year}-{start_month_text}_tm_{year}-{end_month_text}"
            title = f"Uren registratie {calendar_id} voor {year}-{start_month_text} t/m {year}-{end_month_text}"
        else:
            file_name = f"{username}_{year}-{start_month_text}"
            title = f"Uren registratie {calendar_id} voor {year}-{start_month_text}"
        # Format time delta's without seconds (HH:MM)
        def format_timedelta(td):
            total_seconds = int(td.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            return f"{hours}:{minutes:02d}"
        frame["duration"] = frame["duration"].apply(format_timedelta)
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
            fd.write(report.render(title=title, table=frame.to_html(index=False), total_hours=total_hours))
        # Create PDF
        with ctx.cd(os.path.join("future_fashion", "reports")):
            ctx.run(f"wkhtmltopdf {file_name}.html {file_name}.pdf")
    # CLI output
    print(f"Total hours: {total_hours}")
    print(f"Total time: {floor(total_hours/8)} working days and {total_hours%8} hours")
    if not to_file:
        print(f"Time category summary:")
        print(frame[["category", "duration"]].groupby(["category"]).sum())
