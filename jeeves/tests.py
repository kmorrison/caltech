from datetime import timedelta
from datetime import datetime

from django.test import TestCase
from django.test.client import Client

from jeeves import models
from jeeves import views

DATEPICKER_FORMAT = "%Y-%m-%d %H:%M"

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
        now = datetime.now().replace(second=0, microsecond=0)
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
        now = datetime.now().replace(second=0, microsecond=0)
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
                set((self.captain, self.first_mate)),
                set(views.get_interviewers(self.req)),
        )

    def test_include(self):
        self.assertEqual(
                set((self.captain, self.first_mate, self.pilot)),
                set(views.get_interviewers(self.req, also_include=[self.pilot])),
        )

    def test_exclude(self):
        self.assertEqual(
                set((self.captain,)),
                set(views.get_interviewers(self.req, dont_include=[self.first_mate])),
        )

    def test_include_already_in(self):
        self.assertEqual(
                [self.captain, self.first_mate],
                list(views.get_interviewers(self.req, also_include=[self.first_mate])),
        )

    def test_exclude_non_existent(self):
        self.assertEqual(
                set((self.captain, self.first_mate)),
                set(views.get_interviewers(self.req, dont_include=[self.pilot])),
        )

    def test_exclude_trumps_include(self):
        self.assertEqual(
                set((self.captain, self.first_mate)),
                set(views.get_interviewers(self.req, also_include=[self.pilot], dont_include=[self.pilot])),
        )
