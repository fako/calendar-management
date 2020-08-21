from invoke import Collection
from future_fashion.tasks import report_events as ff_report_events
from datascope.tasks import report_events as ds_report_events
from nautilus.tasks import sync_calendar_permissions


namespace = Collection(
    Collection("ff", ff_report_events),
    Collection("ds", ds_report_events),
    Collection("nau", sync_calendar_permissions)
)
