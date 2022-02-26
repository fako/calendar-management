from invoke import Collection
from future_fashion.tasks import report_events as ff_report_events
from datascope.tasks import report_events as ds_report_events, report_week, report_quarter
from nautilus.tasks import sync_calendar_permissions, generate_groups_overview


namespace = Collection(
    Collection("ff", ff_report_events),
    Collection("ds", ds_report_events, report_week, report_quarter),
    Collection("nau", sync_calendar_permissions, generate_groups_overview)
)
