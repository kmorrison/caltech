from datetime import timedelta
from datetime import datetime
import itertools

import pytz

from caltech import settings

TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class TimePeriod(object):

    def __init__(self, start_time, end_time):
        self.start_time = start_time
        self.end_time = end_time

    def __repr__(self):
        return "(%s, %s)" % (self.start_time, self.end_time)


# TODO: time_lib?
def format_datetime_utc(dt):
    return dt.astimezone(pytz.utc).strftime(TIME_FORMAT)

def parse_utc_datetime(dt):
    parsed = datetime.strptime(dt, TIME_FORMAT).replace(second=0).replace(tzinfo=pytz.utc)
    # Google gives us back times in UTC
    return parsed.astimezone(pytz.timezone(settings.TIME_ZONE))

def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = itertools.tee(iterable)
    next(b, None)
    return itertools.izip(a, b)

def collapse_times(time_pairs):
    if len(time_pairs) <= 1:
        return time_pairs

    time_pairs = sorted(time_pairs)

    tmp_first = None
    collapsed_times = []
    # Collapse adjecent time-blocks together into a single block
    for chunk1, chunk2 in pairwise(time_pairs):
        if chunk1[1] >= chunk2[0]:
            if tmp_first is None:
                tmp_first = chunk1[0]
        else:
            if tmp_first is None:
                collapsed_times.append(chunk1)
            else:
                collapsed_times.append((tmp_first, chunk1[1]))
                tmp_first = None

    if tmp_first is None:
        collapsed_times.append(chunk2)
    else:
        collapsed_times.append((tmp_first, chunk2[1]))

    return collapsed_times

def calculate_free_times(busy_times, start_time, end_time):
    collapsed_busy_times = collapse_times(busy_times)

    # Turn busy times into free times
    free_times = []
    for chunk1, chunk2 in pairwise(collapsed_busy_times):
        if chunk1[0] == start_time or chunk2[1] == end_time:
            continue

        free_times.append((chunk1[1], chunk2[0]))
    return free_times
