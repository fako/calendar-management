from invoke import Collection
from future_fashion.tasks import list_events as ff_list_events


namespace = Collection(
    Collection("ff", ff_list_events)
)
