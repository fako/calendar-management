from invoke import Collection
from future_fashion.tasks import report_events as ff_report_events


namespace = Collection(
    Collection("ff", ff_report_events)
)
