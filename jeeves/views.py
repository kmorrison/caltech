import simplejson
import pytz
import time

from datetime import date
from datetime import datetime
from datetime import timedelta
from itertools import groupby
import operator

from django import forms
from django.shortcuts import render
from django.shortcuts import redirect
from django.shortcuts import render_to_response
from django.shortcuts import redirect
from django.template import RequestContext
from django.http import HttpResponse

from jeeves import models
from jeeves import rules
from jeeves.calendar import schedule_calculator
from jeeves.calendar.client import calendar_client
from jeeves.calendar.lib import TimePeriod

from caltech import secret
from caltech import settings

# TODO: Clearly the wrong place for this
TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
START_HOUR = 9
HOURS_PER_DAY = 10
CHUNKS_PER_HOUR = 4  # Must divide evenly into 60
SCHEDULE_TIME_FORMAT = "%I:%M"

# TODO: Where does this go?
def all_reqs():
    return models.Requisition.objects.all()

def all_interviewers():
    return models.Interviewer.objects.all()

def all_times():
    hours = [str(num).zfill(2) for num in range(0, 24)]
    minutes = ['00', '15', '30', '45']
    times = []
    for hour in hours:
      for minute in minutes:
          times.append(models.TimeChoice('{hour}:{minute}:00'.format(hour=hour, minute=minute)))
    return times

def all_interview_types():
    return [
      models.InterviewTypeChoice(models.InterviewType.ON_SITE),
      models.InterviewTypeChoice(models.InterviewType.SKYPE),
    ]

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

def get_interview_groups_with_requirements(requisition, interview_type, also_include=None, dont_include=None):
    requirements = rules.get_interview_requirements(requisition, interview_type)
    interviewer_groups = rules.get_interview_group(requirements)

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

def interview_post(request):
    interview_form = dict(request.POST)
    del interview_form['csrfmiddlewaretoken']
    interview_type = int(interview_form.pop('interview_type')[0])
    recruiter_id = interview_form.pop('recruiter_id')
    candidate_name = interview_form.pop('candidate_name')
    interviews = map(dict, zip(*[[(k, v) for v in value] for k, value in interview_form.items()]))
    for interview_slot in interviews:
        interview_slot['start_time'] = datetime.fromtimestamp(float(interview_slot['start_time']))
        interview_slot['start_time'].replace(tzinfo=pytz.timezone(settings.TIME_ZONE))
        interview_slot['end_time'] = datetime.fromtimestamp(float(interview_slot['end_time']))
        interview_slot['end_time'].replace(tzinfo=pytz.timezone(settings.TIME_ZONE))

        interview_slot['interviewer_id'] = models.Interviewer.objects.get(name=interview_slot['interviewer'].split('@')[0]).id
        interview_slot['room_id'] = models.Room.objects.get(display_name=interview_slot['room']).id
        interview_slot['candidate_name'] = candidate_name[0]

    schedule_calculator.persist_interview(interviews, interview_type)

    # Sorting so we can make the content in the right order.
    interviews = sorted(interviews, key=lambda x: x['start_time'])

    body_content = '\n'.join(create_calendar_event_content(interviews))

    start_time = datetime.fromtimestamp(float(interview_form['room_start_time'][0]))
    start_time = start_time.replace(tzinfo=pytz.timezone(settings.TIME_ZONE))

    end_time = datetime.fromtimestamp(float(interview_form['room_end_time'][0]))
    end_time = end_time.replace(tzinfo=pytz.timezone(settings.TIME_ZONE))

    interview_type_string = models.InterviewTypeChoice(interview_type).display_string

    calendar_response = calendar_client.create_event(
        '%(type)s - %(candidate)s (%(requisition)s)' % {
            'type': interview_type_string,
            'candidate': candidate_name[0],
            'requisition': interview_form['requisition'][0],
        },
        body_content,
        start_time,
        end_time,
        interview_form['external_id'][0],
        interview_form['room'][0],
    )

    return redirect('/new_scheduler?success=1')

def create_calendar_event_content(interviews):
    list_of_interviewers = []

    for interview in interviews:
            list_of_interviewers.append('%(time)s: %(name)s' % { 'time': interview['start_time'].timetz().strftime(SCHEDULE_TIME_FORMAT), 'name': interview['interviewer'] })

    return list_of_interviewers

def get_color_group_for_requisition(requisition):
    colors = ['red', 'orange', 'green', 'blue', 'purple', 'pink', 'grey', 'magenta']
    req_to_color = {}
    for idx, req in enumerate(all_reqs()):
      if str(req).lower() == requisition.lower():
          return colors[idx%len(colors)]

def tracker(request):
    if 'start_date' not in request.GET:
        today = date.today()
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(days=5)
    else:
        start_date = date.fromtimestamp(float(request.GET['start_date']))
        end_date = start_date + timedelta(days=5)

    last_week_start = start_date - timedelta(days=7)
    next_week_start = start_date + timedelta(days=7)

    tracker_dict = schedule_calculator.get_interviews_with_all_interviewers(
        start_date,
        end_date
    )

    for group, interviewer_dict in tracker_dict.iteritems():
        group_dict = {}
        group_dict['interviewer'] = interviewer_dict
        group_dict['color_group'] = get_color_group_for_requisition(group)

        for interviewer_name, interviews in group_dict['interviewer'].iteritems():
            num_interviews_for_interviewer = 0
            interviews.sort(key=operator.itemgetter('day_of_week'))
            interviews_dict_by_day_of_week = {}
            for day_of_week, interview_list in groupby(interviews, key=lambda x:x['day_of_week']):
                grouped_interview_list = list(interview_list)
                for interview in grouped_interview_list:
                    start_time = convert_times_to_pst(interview['start_time'])
                    end_time = convert_times_to_pst(interview['end_time'])

                    interview['date'] = start_time.date().strftime("%x")
                    interview['start_time'] = start_time.strftime("%I:%M")
                    interview['end_time'] = end_time.strftime("%I:%M")
                interviews_dict_by_day_of_week[day_of_week] = {'num_interviews': len(grouped_interview_list), 'interviews': grouped_interview_list}
                num_interviews_for_interviewer += len(grouped_interview_list)
            interviewer_info_dict = {
                'interviews': interviews_dict_by_day_of_week,
                'num_interviews': num_interviews_for_interviewer,
            }
            group_dict['interviewer'][interviewer_name] = interviewer_info_dict
        tracker_dict[group] = group_dict

    date_format = "%m/%d"
    week_info = (
        ('Mon', start_date.strftime(date_format)),
        ('Tue', (start_date + timedelta(days=1)).strftime(date_format)),
        ('Wed', (start_date + timedelta(days=2)).strftime(date_format)),
        ('Thu', (start_date + timedelta(days=3)).strftime(date_format)),
        ('Fri', (start_date + timedelta(days=4)).strftime(date_format)),
    )

    return render(
            request,
            'tracker.html',
            dict(
                tracker_dict = tracker_dict,
                last_week_start = time.mktime(last_week_start.timetuple()),
                next_week_start = time.mktime(next_week_start.timetuple()),
                week_info = week_info,
                all_interviewers=all_interviewers(),
                context_instance=RequestContext(request)
            )
    )


def convert_times_to_pst(dt):
    return dt.astimezone(pytz.timezone('US/Pacific'))


def new_scheduler(request):
    success = 1 if 'success' in request.GET else 0
    context = dict(
      itypes=all_interview_types(),
      reqs=all_reqs(),
      times=all_times(),
      success=success,
      recruiters=schedule_calculator.get_all_recruiters()
    )
    return render_to_response('new_scheduler.html', context, context_instance=RequestContext(request))

def modify_interview(request):
    form_data = request.POST
    if form_data['hovercard-submit'] == 'Modify':
        if form_data['interview_slot_id'] and form_data['interviewer_id']:
            schedule_calculator.change_interviewer(form_data['interview_slot_id'], form_data['interviewer_id'])
    elif form_data['hovercard-submit'] == 'Remove':
        if form_data['interview_id']:
            schedule_calculator.delete_interview(form_data['interview_id'])

    return redirect('/tracker/')

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

def get_time_period(start_time, end_time, date):
    def convert_form_datetime_to_sql_datetime(date, time):
      date_time = datetime.strptime("{date} {time}".format(date=date, time=time), "%m/%d/%Y %H:%M:%S")
      date_time = date_time.replace(tzinfo=pytz.timezone(settings.TIME_ZONE))
      return date_time

    start_datetime = convert_form_datetime_to_sql_datetime(date, start_time)
    end_datetime = convert_form_datetime_to_sql_datetime(date, end_time)
    return TimePeriod(start_datetime, end_datetime)

def error_check_scheduler_form_post(form):
    error_fields = []
    for field, value in form.iteritems():
        if not value:
            error_fields.append(field)
    if error_fields:
        return False, error_fields
    else:
        return True, []


def get_interviewer_set(interviewer_type, requisition):
    return []

def new_scheduler_post(request):
    form_data = request.POST
    interview_type = int(form_data['interview_type'])
    candidate_name = form_data['candidate_name']
    # error checking for request.POST
    form_is_valid, error_fields = error_check_scheduler_form_post(form_data)

    if not form_is_valid:
        return HttpResponse(simplejson.dumps({'form_is_valid': form_is_valid, 'error_fields': error_fields}))

    requisition = models.Requisition.objects.get(name=form_data['requisition'])
    interviewer_groups = get_interview_groups_with_requirements(requisition, interview_type)
    time_period = get_time_period(form_data['start_time'], form_data['end_time'], form_data['date'])

    calendar_responses = [
        calendar_client.get_calendars(
            interviewer_group.interviewers,
            time_period)
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
            time_period=time_period,
    )
    if not schedules:
        return HttpResponse(simplejson.dumps({'form_is_valid': False, 'error_fields': ['no result found']}))

    scheduler_post_result = {
        'form_is_valid': form_is_valid,
        'data': _dump_schedules_into_json(schedules),
        'interview_type': interview_type,
        'candidate_name': candidate_name
    }

    return HttpResponse(simplejson.dumps(scheduler_post_result), mimetype='application/json')


def _dump_schedules_into_json(schedules):
    data = []
    for schedule in schedules:
        schedule_data = {
            'priority': schedule.priority,
            'room': _dump_interview_slot_to_dictionary(schedule.room),
        }

        interview_slots = []
        for slot in schedule.interview_slots:
            interview_slots.append(_dump_interview_slot_to_dictionary(slot))
        schedule_data['interview_slots'] = interview_slots

        data.append(schedule_data)

    return data

def _dump_interview_slot_to_dictionary(slot):
    data = slot.__dict__
    data['start_datetime'] = time.mktime(data['start_time'].timetuple())
    data['end_datetime'] = time.mktime(data['end_time'].timetuple())
    data['start_time'] = data['start_time'].strftime(SCHEDULE_TIME_FORMAT)
    data['end_time'] = data['end_time'].strftime(SCHEDULE_TIME_FORMAT)

    return data
