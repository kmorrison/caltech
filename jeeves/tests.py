from datetime import timedelta
from datetime import datetime

from django.test import TestCase
from django.test.client import Client
import pytz

from caltech import settings
from jeeves import models
from jeeves import views
from jeeves.calendar import schedule_calculator
from jeeves.calendar import lib
from jeeves.calendar import client

DATEPICKER_FORMAT = "%Y-%m-%d %H:%M:%S"

class BaseTestCase(TestCase):
    def setUp(self):
        self.captain = models.Interviewer.objects.create(name='malcolm', domain='reynolds.com')
        self.first_mate = models.Interviewer.objects.create(name='zoe', domain='washburn.com')
        self.pilot = models.Interviewer.objects.create(name='wash', domain='leaf.com')

        self.req = models.Requisition.objects.create(name='Mechanic')

        self.req.interviewers.add(self.captain, self.first_mate)


class ModelsTestCase(BaseTestCase):
    def test_address(self):
        self.assertEqual(self.captain.address, 'malcolm@reynolds.com')

    def test_relation(self):
        first_req = self.captain.requisitions.all()[0]
        self.assertEqual(first_req, self.req)

        interviewers = self.req.interviewers.all()
        self.assertEqual([self.captain.id, self.first_mate.id], [i.id for i in interviewers])

class FindTimesViewTestCase(BaseTestCase):

    def setUp(self):
        super(FindTimesViewTestCase, self).setUp()
        self.c = Client()

    def test_form_view(self):
        response = self.c.get('/find_times/')
        self.assertEqual(response.status_code, 200)

        form = response.context['find_times_form']
        req_select = form.fields['requisition']
        self.assertEqual(req_select.queryset[0], self.req)

        interviewer_set = set((self.captain, self.first_mate, self.pilot))
        also_include_select = form.fields['also_include']
        self.assertEqual(interviewer_set, set(also_include_select.queryset))

        dont_include_select = form.fields['dont_include']
        self.assertEqual(interviewer_set, set(dont_include_select.queryset))

    def _submit_form_with_data(
            self,
            expected_req,
            expect_response=200,
            expected_include=None,
            expected_exclude=None,
            expected_start_time=None,
            expected_end_time=None,
            **form_data
    ):
        if expected_include is None:
            expected_include = []
        if expected_exclude is None:
            expected_exclude = []
        # Setup time input, which is required and a pain to setup every time
        now = datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(pytz.timezone(settings.TIME_ZONE)).replace(second=0, microsecond=0)
        tomorrow = now + timedelta(days=1)
        form_data.setdefault('start_time', now.strftime(DATEPICKER_FORMAT),)
        form_data.setdefault('end_time', tomorrow.strftime(DATEPICKER_FORMAT),)

        response = self.c.get('/find_times/')
        self.assertEqual(response.status_code, 200)

        form = response.context['find_times_form']
        form.data.update(form_data)

        post_response = self.c.post('/find_times_post/', form.data)
        self.assertEqual(post_response.status_code, 200)

        bound_form = post_response.context['find_times_form']
        req, include, exclude = bound_form.requisition_and_custom_interviewers
        self.assertEqual(req, expected_req)
        self.assertEqual(set(include), set(expected_include))
        self.assertEqual(set(exclude), set(expected_exclude))

        if expected_start_time is not None:
            self.assertEqual(bound_form.cleaned_data['start_time'], expected_start_time)
        if expected_end_time is not None:
            self.assertEqual(bound_form.cleaned_data['end_time'], expected_end_time)
        return post_response

    def test_form_submit(self):
        self._submit_form_with_data(
                self.req,
                requisition=self.req.id,
        )

    def test_inclusion(self):
        self._submit_form_with_data(
                self.req,
                expected_include=[self.pilot],

                requisition=self.req.id,
                also_include=[self.pilot.id],
        )

    def test_exclusion(self):
        self._submit_form_with_data(
                self.req,
                expected_exclude=[self.first_mate],

                requisition=self.req.id,
                dont_include=[self.first_mate.id],
        )

    def test_times(self):
        now = datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(pytz.timezone(settings.TIME_ZONE)).replace(second=0, microsecond=0)
        tomorrow = now + timedelta(days=1)
        self._submit_form_with_data(
                self.req,
                expected_start_time=now,
                expected_end_time=tomorrow,

                requisition=self.req.id,
                start_time=now.strftime(DATEPICKER_FORMAT),
                end_time=tomorrow.strftime(DATEPICKER_FORMAT),
        )

class GetInterviewersTestCase(BaseTestCase):

    def test_get_interviewers(self):
        self.assertEqual(
                (set(), set((self.captain, self.first_mate))),
                views.get_interviewers(self.req),
        )

    def test_include(self):
        self.assertEqual(
                (set((self.pilot,)), set((self.captain, self.first_mate))),
                views.get_interviewers(self.req, also_include=[self.pilot]),
        )

    def test_exclude(self):
        self.assertEqual(
                (set(), set((self.captain,))),
                views.get_interviewers(self.req, dont_include=[self.first_mate]),
        )

    def test_include_already_in(self):
        self.assertEqual(
                (set((self.first_mate,)), set((self.captain,))),
                views.get_interviewers(self.req, also_include=[self.first_mate]),
        )

    def test_exclude_non_existent(self):
        self.assertEqual(
                (set(), set((self.captain, self.first_mate))),
                views.get_interviewers(self.req, dont_include=[self.pilot]),
        )

    def test_exclude_doesnt_trump_include(self):
        self.assertEqual(
                (set((self.pilot,)), set((self.captain, self.first_mate))),
                views.get_interviewers(self.req, also_include=[self.pilot], dont_include=[self.pilot]),
        )

class CalendarClientTestCase(BaseTestCase):

    def setUp(self):
        super(CalendarClientTestCase, self).setUp()
        self.calendar_client = client.calendar_client
        now = datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(pytz.timezone(settings.TIME_ZONE)).replace(second=0, microsecond=0)
        tomorrow = now + timedelta(days=1)
        self.time_period = lib.TimePeriod(now, tomorrow)

    def test_one_interviewer(self):
        calendar_response = self.calendar_client.get_calendars([self.captain], [], self.time_period)
        self.assertEqual(len(calendar_response.interview_calendars), 1)
        self.assertEqual(self.captain, calendar_response.interview_calendars[0].interviewer)

    def test_two_interviewers(self):
        calendar_response = self.calendar_client.get_calendars([self.captain, self.first_mate], [], self.time_period)
        self.assertEqual(len(calendar_response.interview_calendars), 2)
        self.assertEqual([self.captain, self.first_mate], [ic.interviewer for ic in calendar_response.interview_calendars])

    def test_time_bounds(self):
        calendar_response = self.calendar_client.get_calendars([self.captain], [], self.time_period)
        self.assertEqual(len(calendar_response.interview_calendars), 1)
        self.assertEqual(self.captain, calendar_response.interview_calendars[0].interviewer)

        busy_times = calendar_response.interview_calendars[0].busy_times
        self.assertTrue(self.time_period.start_time <= busy_times[0].start_time)

class SchedulerTestCase(BaseTestCase):

    def setUp(self):
        super(SchedulerTestCase, self).setUp()
        now = datetime(2012, 9, 27, 15, 0).replace(tzinfo=pytz.utc).astimezone(pytz.timezone(settings.TIME_ZONE)).replace(second=0, microsecond=0)
        later = now + timedelta(hours=4)
        self.time_period = lib.TimePeriod(now, later)
        self.fifteen_minutes = lib.TimePeriod(self.time_period.start_time, self.time_period.start_time + timedelta(minutes=15))

        self.default_break = lib.time_period_of_length_after_time(self.time_period.start_time, 75, 0)

        self.test_service_client = client.TestServiceClient()
        self.test_service_client.register_busyness(self.captain.address, self.fifteen_minutes.shift_minutes(60))
        self.test_service_client.register_busyness(self.captain.address, self.fifteen_minutes.shift_minutes(75))
        self.test_service_client.register_busyness(self.captain.address, self.fifteen_minutes.shift_minutes(90))
        self.test_service_client.register_busyness(self.captain.address, self.fifteen_minutes.shift_minutes(105))

        self.calendar_client = client.Client(self.test_service_client)

    def test_possible(self):
        calendar_response = self.calendar_client.get_calendars([self.captain, self.first_mate], [], self.time_period)
        required_interviewers, optional_interviewers = calendar_response.winnow_by_interviewers([self.captain.name])
        schedules = schedule_calculator.calculate_schedules(
                required_interviewers,
                optional_interviewers,
                2,
                self.time_period,
                possible_break=self.default_break,
        )

        self.assertEqual(len(schedules), 1)

    def test_break_before_and_after(self):
        calendar_response = self.calendar_client.get_calendars([self.captain, self.first_mate], [], self.time_period)
        required_interviewers, optional_interviewers = calendar_response.winnow_by_interviewers([self.first_mate.name])

        schedules = schedule_calculator.calculate_schedules(
                required_interviewers,
                optional_interviewers,
                1,
                self.time_period,
                possible_break=self.default_break.shift_minutes(45),
        )

        self.assertEqual(len(schedules), 2)

    def test_no_break(self):
        calendar_response = self.calendar_client.get_calendars([self.captain, self.first_mate], [], self.time_period)
        required_interviewers, optional_interviewers = calendar_response.winnow_by_interviewers([self.first_mate.name])

        schedules = schedule_calculator.calculate_schedules(
                required_interviewers,
                optional_interviewers,
                1,
                self.time_period,
        )

        self.assertEqual(len(schedules), 13)
