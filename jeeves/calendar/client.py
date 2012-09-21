from datetime import timedelta
from datetime import datetime
import random

from caltech import secret
from . import schedule
from . import lib

class CalendarQuery(object):

    def __init__(self, interviewers, time_period):
        self.interviewers = interviewers
        self.time_period = time_period

    def to_query_body(self):
        return dict(
                timeMin=lib.format_datetime_utc(self.time_period.start_time),
                timeMax=lib.format_datetime_utc(self.time_period.end_time),
                items=[dict(id=interviewer.address) for interviewer in self.interviewers],
        )

class InterviewCalendar(object):

    def __init__(self, interviewer, period_of_interest, start_end_pairs):
        self.interviewer = interviewer

        busy_times = [(lib.parse_utc_datetime(dt_dict['start']), lib.parse_utc_datetime(dt_dict['end'])) for dt_dict in start_end_pairs]
        self.busy_times = [
                lib.TimePeriod(start_time, end_time)
                for (start_time, end_time) in lib.collapse_times(
                    busy_times,
                )
        ]

        self.free_times = [
                lib.TimePeriod(start_time, end_time)
                for (start_time, end_time) in lib.calculate_free_times(
                    busy_times,
                    period_of_interest.start_time,
                    period_of_interest.end_time
                )
        ]


class CalendarResponse(object):

    def __init__(self, calendar_query, service_response):
        calendars = service_response['calendars']
        self.interview_calendars = [InterviewCalendar(interviewer, calendar_query.time_period, calendars[interviewer.address]['busy'])
                for interviewer in calendar_query.interviewers
        ]


class Client(object):

    def __init__(self):
        if secret.use_mock:
            self._service_client = MockServiceClient()
        else:
            self._service_client = ServiceClient(schedule.build_service())

    def get_calendars(self, interviewers, time_period):
        return self._service_client.process_calendar_query(CalendarQuery(interviewers, time_period))

class MockServiceClient(object):

    def process_calendar_query(self, calendar_query):
        mock_service_response = dict(
                calendars=dict(
                    (interviewer.address, self._build_random_calendar(interviewer, calendar_query.time_period))
                    for interviewer in calendar_query.interviewers
                )
        )
        return CalendarResponse(
                calendar_query,
                mock_service_response,
        )

    def _build_random_calendar(self, interviewer, time_period, saturation_coefficient=0.33, minutes_of_resolution=15):
        busy_times = []
        current_time = time_period.start_time
        while current_time < time_period.end_time:
            new_time = current_time + timedelta(minutes=minutes_of_resolution)

            if random.random() < saturation_coefficient:
                busy_times.append(dict(start=lib.format_datetime_utc(current_time), end=lib.format_datetime_utc(new_time)))

            current_time = new_time

        return dict(busy=busy_times)


class ServiceClient(object):

    def __init__(self, service):
        self._service = service

    def process_calendar_query(self, calendar_query):
        return CalendarResponse(
                calendar_query,
                self._service.freebusy().query(body=calendar_query.to_query_body()).execute()
        )


calendar_client = Client()
