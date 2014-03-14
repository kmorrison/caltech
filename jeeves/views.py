from datetime import datetime

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
START_HOUR = 9
HOURS_PER_DAY = 10
CHUNKS_PER_HOUR = 4  # Must divide evenly into 60

# TODO: Where does this go?
def all_reqs():
    return models.Requisition.objects.all()

def all_interviewers():
    return models.Interviewer.objects.all()

def all_times():
    minutes = ['00', '15', '30', '45']
    hours = [str(num) for num in range(1, 13)]
    periods = ['am', 'pm']
    times = []
    for period in periods:
      for hour in hours:
        for minute in minutes:
            times.append('%s:%s %s' % (hour, minute, period))
    return times

def get_interviewers(requisition, also_include=None, dont_include=None, squash_groups=True):
    requisition = models.Requisition.objects.get(id=requisition.id)
    interviewers = set(requisition.interviewers.all())
    required_interviewers = set()

    if also_include is not None:
        required_interviewers.update(models.Interviewer.objects.filter(id__in=[i.id for i in also_include]))

    if dont_include is not None:
        interviewers -= set(models.Interviewer.objects.filter(id__in=[i.id for i in dont_include]))

    return required_interviewers, interviewers - required_interviewers

def get_interviewer_groups(formset, also_include=None, dont_include=None):
    """Extract interviewers requirements from the form and turn them into InterviewerGroups.
    XXX: This is pretty hacky right now as we transition to formsets on the form
    """
    # TODO: Collapse querys into single, nonlooping query
    requisitions = [form.cleaned_data['requisition'] for form in formset if form.cleaned_data]
    requisitions = [models.Requisition.objects.get(id=req.id) for req in requisitions]
    interviewers_by_requisition = [set(requisition.interviewers.all()) for requisition in requisitions]
    interviewer_groups = []
    if dont_include:
        dont_interviewers = set(models.Interviewer.objects.filter(id__in=[i.id for i in also_include]))
        interviewers_by_requisition = [interviewers_by_req - dont_interviewers for interviewers_by_req in interviewers_by_requisition]

    if also_include:
        must_interviewers = set(models.Interviewer.objects.filter(id__in=[i.id for i in also_include]))
        interviewer_groups.append((len(must_interviewers), must_interviewers))

    interviewer_groups += [(
        form.cleaned_data['num_required'],
        interviewers,
        ) for interviewers, form in zip(interviewers_by_requisition, formset)
    ]

    # Reduce interviewer sets
    interviewer_groups = sorted(interviewer_groups, lambda x,y: len(y))
    for i, (_, interviewers) in enumerate(interviewer_groups[:-1]):
        for _, other_interviewers in interviewer_groups[i+1:]:
            other_interviewers.difference_update(interviewers)

    interviewer_groups = [schedule_calculator.InterviewerGroup(*interviewer_group) for interviewer_group in interviewer_groups]
    return interviewer_groups


class FindTimesForm(forms.Form):
    requisition = forms.ModelChoiceField(queryset=all_reqs(), initial=getattr(secret, 'preferred_requisition_id', None) or 1)

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


class RequisitionScheduleForm(forms.Form):
    requisition = forms.ModelChoiceField(
        queryset=all_reqs(),
        required=False,
    )
    num_required = forms.TypedChoiceField([(i, i) for i in xrange(1, 10)], coerce=int, initial=1)

RequisitionScheduleFormset = forms.formsets.formset_factory(RequisitionScheduleForm, extra=2)


class SuggestScheduleForm(forms.Form):
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

    break_start_time = forms.DateTimeField(required=False, label='Break Start Time (optional)')
    break_end_time = forms.DateTimeField(required=False, label='Break End Time (optional)')

    @property
    def time_period(self):
        return TimePeriod(self.cleaned_data['start_time'], self.cleaned_data['end_time'])

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

        calendar_response = calendar_client.get_calendars(
            required_interviewers | optional_interviewers,
            find_times_form.time_period,
        )

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
        requisition_formset=RequisitionScheduleFormset(
            initial=[dict(
                num_required=2,
                requisition=getattr(secret, 'preferred_requisition_id', None) or 1,
            )]
        ),
        scheduler_form=SuggestScheduleForm(),
    )
    return render_to_response('scheduler.html', context, context_instance=RequestContext(request))

def new_scheduler(request):
    context = dict(
      reqs=all_reqs(),
      times=all_times()
    )
    return render_to_response('new_scheduler.html', context)

def scheduler_post(request):
    requisition_formset = RequisitionScheduleFormset(request.POST)
    scheduler_form = SuggestScheduleForm(request.POST)
    valid_submission = scheduler_form.is_valid() and requisition_formset.is_valid()
    schedules = []
    if not valid_submission:
        return render(
                request,
                'scheduler.html',
                dict(
                    requisition_formset=requisition_formset,
                    scheduler_form=scheduler_form,
                    valid_submission=valid_submission,
                    schedules=schedules,
                )
        )

    interviewer_groups = get_interviewer_groups(
            requisition_formset,
            also_include=scheduler_form.cleaned_data['also_include'],
            dont_include=scheduler_form.cleaned_data['dont_include'],
    )

    calendar_responses = [
        calendar_client.get_calendars(
            interviewer_group.interviewers,
            scheduler_form.time_period)
        for interviewer_group in interviewer_groups
        if interviewer_group.num_required
    ]

    interviewer_groups_with_calendars = [
        schedule_calculator.InterviewerGroup(
            interviewers=calendar_response.interview_calendars,
            num_required=interviewer_group.num_required,
        )
        for calendar_response, interviewer_group in zip(calendar_responses, interviewer_groups)
    ]

    schedules = schedule_calculator.calculate_schedules(
            interviewer_groups_with_calendars,
            time_period=scheduler_form.time_period,
            possible_break=scheduler_form.possible_break,
    )

    return render(
            request,
            'scheduler.html',
            dict(
                requisition_formset=requisition_formset,
                scheduler_form=scheduler_form,
                valid_submission=valid_submission,
                schedules=schedules,
            )
    )
