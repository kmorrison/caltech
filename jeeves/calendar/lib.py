import itertools

def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = itertools.tee(iterable)
    next(b, None)
    return itertools.izip(a, b)

def collapse_times(time_pairs):
    time_pairs = sorted(time_pairs)

    tmp_first = None
    collapsed_times = []
    # Collapse adjecent time-blocks together into a single block
    for chunk1, chunk2 in pairwise(time_pairs):
        if chunk1[1] >= chunk2[0]:
            if tmp_first is None:
                tmp_first = min(chunk1[1], chunk2[0])
        else:
            if tmp_first is None:
                collapsed_times.append(chunk1)
            else:
                collapsed_times.append((tmp_first, chunk1[1]))
                tmp_first = None
    if tmp_first is not None:
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
