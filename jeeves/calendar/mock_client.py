import random

class MockClient(object):

    def get_calendars(
            interviewers,
            start_time,
            end_time,
            saturation_coefficient=0.33,
            minutes_of_resolution=15,
    ):
        pass

    def _build_random_calendar(interviewer, start_time, end_time, saturation_coefficient, minutes_of_resolution):
        free_times = []
        current_time = start_time
        while current_time < end_time:
            new_time = current_time + timedelta(minutes=minutes_of_resolution)

            if random.random() > saturation_coefficient:
                free_times.append(current_time, new_time)

            current_time = new_time

        return free_times

