from datetime import timedelta
from datetime import datetime

from django.http import HttpResponse
from django import forms
from django.shortcuts import render
from django.shortcuts import render_to_response
from django.template import RequestContext

from jeeves import models
from jeeves.calendar import schedule_calculator
from jeeves.calendar.client import calendar_client
from jeeves.calendar.lib import TimePeriod

from caltech import secret

# TODO: Clearly the wrong place for this
TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
START_HOUR = 8
HOURS_PER_DAY = 11
CHUNKS_PER_HOUR = 12  # Must divide evenly into 60

# TODO: Where does this go?
def all_reqs():
    return models.Requisition.objects.all()

def all_interviewers():
    return models.Interviewer.objects.all()

def get_interviewers(requisition, also_include=None, dont_include=None):
    requisition = models.Requisition.objects.get(id=requisition.id)
    interviewers = set(requisition.interviewers.all())
    required_interviewers = set()

    if also_include is not None:
        required_interviewers.update(models.Interviewer.objects.filter(id__in=[i.id for i in also_include]))

    if dont_include is not None:
        interviewers -= set(models.Interviewer.objects.filter(id__in=[i.id for i in dont_include]))

    return required_interviewers, interviewers - required_interviewers

class FindTimesForm(forms.Form):
    requisition = forms.ModelChoiceField(queryset=all_reqs(), initial=getattr(secret, 'preferred_requisition_id') or 1)

    start_time = forms.DateTimeField(label='Availability Start Time')
    end_time = forms.DateTimeField(label='Availability End Time')

    also_include = forms.ModelMultipleChoiceField(
            queryset=all_interviewers(),
            required=False,
    )
    dont_include = forms.ModelMultipleChoiceField(
            queryset=all_interviewers(),
            required=False,
            label="Don't Include",
    )

    @property
    def requisition_and_custom_interviewers(self):
        return (
                self.cleaned_data['requisition'],
                self.cleaned_data['also_include'],
                self.cleaned_data['dont_include'],
        )

    @property
    def time_period(self):
        return TimePeriod(self.cleaned_data['start_time'], self.cleaned_data['end_time'])

class SuggestScheduleForm(FindTimesForm):

    number_of_interviewers = forms.TypedChoiceField([(i, i) for i in xrange(1, 10)], coerce=int)

    break_start_time = forms.DateTimeField(required=False, label='Break Start Time (optional)')
    break_end_time = forms.DateTimeField(required=False, label='Break End Time (optional)')

    @property
    def possible_break(self):
        if self.cleaned_data['break_start_time'] is None or  self.cleaned_data['break_end_time'] is None:
            return None
        return TimePeriod(self.cleaned_data['break_start_time'], self.cleaned_data['break_end_time'])


def index(request):
    # TODO: Should this go in static?
    return render_to_response('index.html', {})

def find_times(request):
    context = dict(
            find_times_form=FindTimesForm(),
            START_DATE=datetime.now().isoformat(),
            START_HOUR=START_HOUR,
            HOURS_PER_DAY=HOURS_PER_DAY,
            CHUNKS_PER_HOUR=CHUNKS_PER_HOUR,
    )

    return render_to_response('find_times.html', context, context_instance=RequestContext(request))

def find_times_post(request):
    find_times_form = FindTimesForm(request.POST)
    if find_times_form.is_valid():
        required_interviewers, optional_interviewers = get_interviewers(
                *find_times_form.requisition_and_custom_interviewers
        )

        calendar_response = calendar_client.get_calendars(required_interviewers, optional_interviewers, find_times_form.time_period)

        return render(
                request,
                'find_times.html',
                dict(
                    find_times_form=find_times_form,
                    calendar_response=calendar_response,
                    START_DATE=find_times_form.time_period.start_time.isoformat(),
                    START_HOUR=START_HOUR,
                    HOURS_PER_DAY=HOURS_PER_DAY,
                    CHUNKS_PER_HOUR=CHUNKS_PER_HOUR,
                )
        )

    return render(
            request,
            'find_times.html',
            dict(
                find_times_form=find_times_form,
            )
    )

def scheduler(request):
    context = dict(
            scheduler_form=SuggestScheduleForm(),
    )
    return render_to_response('scheduler.html', context, context_instance=RequestContext(request))

def scheduler_post(request):
    scheduler_form = SuggestScheduleForm(request.POST)
    valid_submission = scheduler_form.is_valid()
    if scheduler_form.is_valid():
        required_interviewers, optional_interviewers = get_interviewers(
                *scheduler_form.requisition_and_custom_interviewers
        )

        calendar_response = calendar_client.get_calendars(required_interviewers, optional_interviewers, scheduler_form.time_period)
        required_interviewers, optional_interviewers = calendar_response.winnow_by_interviewers([interviewer.name for interviewer in scheduler_form.cleaned_data['also_include']])
        schedules = schedule_calculator.calculate_schedules(
                required_interviewers,
                optional_interviewers,
                scheduler_form.cleaned_data['number_of_interviewers'],
                time_period=scheduler_form.time_period,
                possible_break=scheduler_form.possible_break,
        )

    return render(
            request,
            'scheduler.html',
            dict(
                scheduler_form=scheduler_form,
                valid_submission=valid_submission,
                schedules=schedules,
            )
    )
