import random
from datetime import timedelta
from httplib import BadStatusLine

import json
from django.core.serializers.json import DjangoJSONEncoder

from caltech import secret
from . import schedule
from . import lib

MAX_INTERVIEWERS_IN_QUERY = 50

class CalendarQuery(object):

    def __init__(self, interviewers, time_period):
        self.interviewers = random.sample(
                interviewers,
                min(MAX_INTERVIEWERS_IN_QUERY, len(interviewers))
        )
        self.time_period = time_period

    def to_query_body(self, force_all_interviewers=False):
        return dict(
                timeMin=lib.format_datetime_utc(self.time_period.start_time),
                timeMax=lib.format_datetime_utc(self.time_period.end_time),
                items=[dict(id=interviewer.external_id) for interviewer in self.interviewers],
        )

    def __repr__(self):
        return "%s" % ([inte.external_id for inte in self.interviewers],)


class CalendarCreate(object):

    def __init__(self, title, body, time_start, time_end, location, location_name):
        self.title = title
        self.body = body
        self.time_start = time_start
        self.time_end = time_end
        self.location = location
        self.location_name = location_name

    def to_query_body(self):
        return dict(
            calendarId=secret.INTERVIEW_CALENDAR_GROUP_ID,
            start=dict(
                dateTime=lib.format_datetime_utc(self.time_start)
            ),
            end=dict(
                dateTime=lib.format_datetime_utc(self.time_end)
            ),
            summary=self.title,
            description=self.body,
            attendees=[dict(
                email=self.location
            )],
            location=self.location_name,
        )


class InterviewCalendar(object):

    def __init__(self, interviewer, period_of_interest, start_end_pairs):
        self.interviewer = interviewer

        busy_times = [
                (
                    lib.parse_utc_datetime(dt_dict['start']),
                    lib.parse_utc_datetime(dt_dict['end']),
                )
                for dt_dict in start_end_pairs
        ]

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

    def has_availability_during(self, time_period):
        for free_time in self.free_times:
            if free_time.contains(time_period):
                return True
        return False

    def is_blocked_during(self, time_period):
        for busy_time in self.busy_times:
            if busy_time.contains(time_period):
                return True
        return False

    def __repr__(self):
        return self.interviewer.address


class CalendarResponse(object):

    def __init__(self, calendar_query, service_response):
        calendars = service_response['calendars']
        self.interview_calendars = [InterviewCalendar(interviewer, calendar_query.time_period, calendars[interviewer.external_id]['busy'])
                for interviewer in calendar_query.interviewers
                if interviewer.external_id in calendars
        ]
        self._memoize_lookup = {}

    def get_interviewer(self, interviewer_address):
        if interviewer_address in self._memoize_lookup:
            return self._memoize_lookup[interviewer_address]
        interview_calendars = [intcal for intcal in self.interview_calendars if intcal.interviewer.address == interviewer_address]
        assert len(interview_calendars) <= 1
        if interview_calendars:
            intcal = interview_calendars[0]
        else:
            intcal = None
        self._memoize_lookup[interviewer_address] = intcal
        return intcal

    @property
    def interviewers(self):
        return [interview_calendar.interviewer for interview_calendar in self.interview_calendars]

    @property
    def json_interviewers(self):
        return json.dumps([dict(id=interviewer.address, name=interviewer.name) for interviewer in self.interviewers])

    @property
    def json_events(self):
        serialized_calendars = [
                dict(
                    address=interview_calendar.interviewer.address,
                    busy_times=[(busy_period.start_time, busy_period.end_time) for busy_period in interview_calendar.busy_times],
                    display_name=interview_calendar.interviewer.display_name,
                )
                for interview_calendar in self.interview_calendars
        ]
        return json.dumps(sorted(serialized_calendars, key=lambda x: x.get('display_name')), cls=DjangoJSONEncoder)

    def winnow_by_interviewers(self, interviewers):
        selected = []
        not_selected = []
        for interview_calendar in self.interview_calendars:
            if interview_calendar.interviewer.name in interviewers:
                selected.append(interview_calendar)
            else:
                not_selected.append(interview_calendar)
        assert set([interview_calendar.interviewer.name for interview_calendar in selected]) == set(interviewers), "Couldn't find all required interviewers"
        return selected, not_selected


class Client(object):

    def __init__(self, service_client=None):
        if service_client is not None:
            self._service_client = service_client

        elif secret.use_mock:
            self._service_client = MockServiceClient()
        else:
            self._service_client = ServiceClient(schedule.build_service())

    def get_calendars(self, interviewers, time_period):
        return self._service_client.process_calendar_query(CalendarQuery(interviewers, time_period))

    def create_event(self, title, body, time_start, time_end, location, location_name):
        return self._service_client.process_calendar_create(CalendarCreate(title, body, time_start, time_end, location, location_name))

    def delete_event(self, google_event_id):
        return self._service_client.process_calendar_delete(google_event_id)

    def update_event(self, google_event_id, updated_description):
        return self._service_client.process_calendar_update(google_event_id, updated_description)

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

    def _build_random_calendar(self, interviewer, time_period, saturation_coefficient=0.15, minutes_of_resolution=15):
        busy_times = []
        current_time = time_period.start_time
        while current_time < time_period.end_time:
            new_time = current_time + timedelta(minutes=minutes_of_resolution)

            if random.random() < saturation_coefficient:
                busy_times.append(dict(start=lib.format_datetime_utc(current_time), end=lib.format_datetime_utc(new_time)))

            current_time = new_time

        return dict(busy=busy_times)

class TestServiceClient(object):

    def __init__(self):
        self.busyness = dict()

    def register_busyness(self, interviewer, time_period):
        self.busyness.setdefault(interviewer, []).append(time_period)

    def process_calendar_query(self, calendar_query):
        mock_service_response = dict(
                calendars=dict(
                    (interviewer.address, self._regurgitate_registered_busyness(interviewer.address, calendar_query.time_period))
                    for interviewer in calendar_query.interviewers
                )
        )
        return CalendarResponse(
                calendar_query,
                mock_service_response,
        )

    def _regurgitate_registered_busyness(self, interviewer, time_period):
        busy_times = [dict(start=lib.format_datetime_utc(busy_time.start_time), end=lib.format_datetime_utc(busy_time.end_time))
            for busy_time in self.busyness.get(interviewer, [])
        ]
        return dict(busy=busy_times)


class ServiceClient(object):

    def __init__(self, service):
        self._service = service

    @lib.retry_decorator(BadStatusLine)
    def process_calendar_query(self, calendar_query):
        query_body = calendar_query.to_query_body()
        print "query body:"
        #pprint(query_body)
        return CalendarResponse(
                calendar_query,
                self._service.freebusy().query(body=query_body).execute()
        )

    @lib.retry_decorator(BadStatusLine)
    def process_calendar_create(self, calendar):
        body = calendar.to_query_body()

        return self._service.events().insert(calendarId=secret.INTERVIEW_CALENDAR_GROUP_ID, body=body).execute()

    @lib.retry_decorator(BadStatusLine)
    def process_calendar_delete(self, google_event_id):
        return self._service.events().delete(calendarId=secret.INTERVIEW_CALENDAR_GROUP_ID, eventId=google_event_id).execute()

    @lib.retry_decorator(BadStatusLine)
    def process_calendar_update(self, google_event_id, updated_description):
        body = {'description': updated_description}
        return self._service.events().patch(calendarId=secret.INTERVIEW_CALENDAR_GROUP_ID, eventId=google_event_id, body=body).execute()


# Define a module level client that people can import
calendar_client = Client()
