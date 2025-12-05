from invoke import Collection
from datascope.tasks import report_events as ds_report_events, report_week, report_quarter, report_weeks
from nautilus.tasks import sync_calendar_permissions, generate_groups_overview


namespace = Collection(
    Collection("ds", ds_report_events, report_week, report_quarter, report_weeks),
    Collection("nau", sync_calendar_permissions, generate_groups_overview)
)
