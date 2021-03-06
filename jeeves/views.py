import logging
import simplejson
import pytz
import time

import datetime
from datetime import date
from datetime import datetime
from datetime import time as dt_time
from datetime import timedelta
from itertools import groupby
import operator

from django import forms
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.shortcuts import redirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponse

from jeeves import models
from jeeves import rules
from jeeves.calendar import schedule_calculator
from jeeves.calendar.client import calendar_client
from jeeves.calendar.lib import TimePeriod

from caltech import secret
from caltech import settings


logger = logging.getLogger(__name__)
logging.basicConfig(
    filename='log.log',
    level=logging.DEBUG,
    format='%(asctime)s.%(msecs)d %(levelname)s %(module)s - %(funcName)s: %(message)s',
    datefmt="%Y-%m-%d %H:%M:%S"
)


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
      models.InterviewTypeChoice(models.InterviewType.SKYPE_ON_SITE),
    ]


def all_interview_templates():
    return models.InterviewTemplate.objects.all()


def get_interviewers(requisition, also_include=None, dont_include=None, squash_groups=True):
    requisition = models.Requisition.objects.get(id=requisition.id)
    interviewers = set(requisition.interviewers.all())
    required_interviewers = set()

    if also_include is not None:
        required_interviewers.update(models.Interviewer.objects.filter(id__in=[i.id for i in also_include]))

    if dont_include is not None:
        interviewers -= set(models.Interviewer.objects.filter(id__in=[i.id for i in dont_include]))

    return required_interviewers, interviewers - required_interviewers

def get_interview_groups_with_requirements(template_requisitions, also_include=None, dont_include=None):
    interviewer_groups = rules.get_interview_group([(d['number_per_requisition'], d['requisition_id']) for d in template_requisitions])

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


def index(request):
    # TODO: Should this go in static?
    return render_to_response('index.html', {})

@login_required
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


def interview_post(request):
    interview_form = dict(request.POST)
    del interview_form['csrfmiddlewaretoken']
    interview_type = int(interview_form.pop('interview_type')[0])
    recruiter_id = interview_form.pop('recruiter_id')[0]
    interview_template_name = interview_form.pop('interview_template_name')[0]
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


    # Sorting so we can make the content in the right order.
    interviews = sorted(interviews, key=lambda x: x['start_time'])

    body_content = schedule_calculator.create_calendar_body(
        [(interview['start_time'], interview['interviewer']) for interview in interviews],
        models.Recruiter.objects.get(id=recruiter_id),
        request.user,
    )

    start_time = datetime.fromtimestamp(float(interview_form['room_start_time'][0]))
    start_time = start_time.replace(tzinfo=pytz.timezone(settings.TIME_ZONE))

    end_time = datetime.fromtimestamp(float(interview_form['room_end_time'][0]))
    end_time = end_time.replace(tzinfo=pytz.timezone(settings.TIME_ZONE))

    interview_type_string = models.InterviewTypeChoice(interview_type).display_string

    calendar_response = calendar_client.create_event(
        '%(type)s - %(candidate)s (%(interview_template_name)s)' % {
            'type': interview_type_string,
            'candidate': candidate_name[0],
            'interview_template_name': interview_template_name,
        },
        body_content,
        start_time,
        end_time,
        interview_form['external_id'][0],
        interview_form['room'][0],
    )

    schedule_calculator.persist_interview(
        interviews,
        interview_type,
        google_event_id=calendar_response['id'],
        recruiter_id=recruiter_id,
        user_id=request.user.id,
    )

    return redirect('/new_scheduler?success=1')

def get_color_group_for_requisition(index):
    colors = ['white']
    return colors[index%len(colors)]

@login_required
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

    for index, item in enumerate(tracker_dict.iteritems()):
        group, interviewer_dict = item
        group_dict = {}
        group_dict['interviewer'] = interviewer_dict
        group_dict['color_group'] = get_color_group_for_requisition(index)

        for interviewer_name, interviews in group_dict['interviewer'].iteritems():
            num_interviews_for_interviewer = 0
            interviews.sort(key=operator.itemgetter('day_of_week'))
            interviews_dict_by_day_of_week = {}
            day_of_week_to_number_of_interviewers, total_number_of_interviews_for_week = \
                get_number_of_alternate_events_for_interviewer(
                    interviewer_name,
                    last_week_start,
                    next_week_start,
                )
            for day_of_week, interview_list in groupby(interviews, key=lambda x:x['day_of_week']):
                grouped_interview_list = list(interview_list)
                for interview in grouped_interview_list:
                    start_time = convert_times_to_pst(interview['start_time'])
                    end_time = convert_times_to_pst(interview['end_time'])

                    interview['date'] = start_time.date().strftime("%x")
                    interview['start_time'] = start_time.strftime("%I:%M")
                    interview['end_time'] = end_time.strftime("%I:%M")
                interviews_dict_by_day_of_week[day_of_week] = {
                    'num_interviews': len(grouped_interview_list) + day_of_week_to_number_of_interviewers.get(day_of_week, 0),
                    'interviews': grouped_interview_list
                }
                num_interviews_for_interviewer += len(grouped_interview_list)
            interviewer_info_dict = {
                'interviews': interviews_dict_by_day_of_week,
                'num_interviews': num_interviews_for_interviewer,
            }
            group_dict['interviewer'][interviewer_name] = interviewer_info_dict
            update_group_dict_with_alternate_recruiting_events(
                group_dict,
                interviewer_name,
                last_week_start,
                next_week_start
            )
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


def update_group_dict_with_alternate_recruiting_events(
    group_dict,
    interviewer_name,
    last_week_start,
    next_week_start
):
    if interviewer_name not in group_dict['interviewer']:
        return
    interview_info_dict = group_dict['interviewer'][interviewer_name]
    day_of_week_to_number_of_arc, total_number_of_arc_for_week = \
        get_number_of_alternate_events_for_interviewer(
            interviewer_name,
            last_week_start,
            next_week_start,
        )

    interview_info_dict['num_interviews'] += total_number_of_arc_for_week

    for day_of_week, number_of_arc in day_of_week_to_number_of_arc.iteritems():
        if day_of_week not in interview_info_dict['interviews']:
            interview_info_dict['interviews'][day_of_week] = {
                'num_interviews': 0,
                'interviews': [],
            }
        interview_info_dict['interviews'][day_of_week]['num_interviews'] += \
            number_of_arc


def get_number_of_alternate_events_for_interviewer(
    interviewer_name,
    start_date,
    end_date
):
    events = models.AlternateRecruitingEvent.objects.filter(
        time__gte=start_date,
        time__lte=end_date,
        interviewer__display_name=interviewer_name,
    )
    day_of_week_to_number_of_arc = {}
    total_number_of_arc_for_week = 0
    for event in events:
        weekday = event.time.weekday()
        if weekday not in day_of_week_to_number_of_arc:
            day_of_week_to_number_of_arc[weekday] = 0
        day_of_week_to_number_of_arc[weekday] += 1
        total_number_of_arc_for_week += 1

    return day_of_week_to_number_of_arc, total_number_of_arc_for_week


def convert_times_to_pst(dt):
    return dt.astimezone(pytz.timezone('US/Pacific'))


@login_required
def new_scheduler(request):
    success = 1 if 'success' in request.GET else 0
    context = dict(
      itypes=all_interview_types(),
      reqs=all_reqs(),
      times=all_times(),
      interview_templates=all_interview_templates(),
      success=success,
      recruiters=schedule_calculator.get_all_recruiters(),
    )
    return render_to_response(
        'new_scheduler.html',
        context,
        context_instance=RequestContext(request),
    )

def modify_interview(request):
    form_data = request.POST
    if form_data['hovercard-submit'] == 'Modify':
        if form_data['interview_slot_id'] and form_data['interviewer_id']:
            schedule_calculator.change_interviewer(form_data['interview_slot_id'], form_data['interviewer_id'])
    elif form_data['hovercard-submit'] == 'Remove':
        if form_data['interview_id']:
            schedule_calculator.delete_interview(form_data['interview_id'])

    return redirect('/tracker/')

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

def determine_break_from_interview_time(time_period, interview_type):
    if interview_type != models.InterviewType.ON_SITE:
        return None
    weekday = time_period.start_time.weekday()
    if weekday != 4:  # Friday
        return None

    tz_info = time_period.start_time.tzinfo
    start_of_break = dt_time(12, 0, tzinfo=tz_info)
    end_of_break = dt_time(13, 30, tzinfo=tz_info)

    date = time_period.start_time.date()
    start_of_break_dt = datetime.combine(date, start_of_break)
    end_of_break_dt = datetime.combine(date, end_of_break)
    break_time_period = TimePeriod(
        start_of_break_dt,
        end_of_break_dt,
    )
    if time_period.contains(break_time_period):
        print "Adding break %s" % break_time_period
        return break_time_period
    return None


def new_scheduler_post(request):
    form_data = request.POST
    candidate_name = form_data['candidate_name']
    interview_template_id = int(form_data['interview_template'])
    # error checking for request.POST
    form_is_valid, error_fields = error_check_scheduler_form_post(form_data)

    if not form_is_valid:
        return HttpResponse(simplejson.dumps({'form_is_valid': form_is_valid, 'error_fields': error_fields}))

    interview_template = models.InterviewTemplate.objects.get(id=interview_template_id)
    interviewer_groups = get_interview_groups_with_requirements(
        interview_template.interviewtemplaterequisition_set.values()
    )
    time_period = get_time_period(
        form_data['start_time'],
        form_data['end_time'],
        form_data['date'],
    )

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

    possible_break = determine_break_from_interview_time(
        time_period,
        interview_template.type,
    )

    schedules = schedule_calculator.calculate_schedules(
            interviewer_groups_with_calendars,
            time_period=time_period,
            interview_type=interview_template.type,
            possible_break=possible_break,
    )
    if not schedules:
        return HttpResponse(simplejson.dumps({'form_is_valid': False, 'error_fields': ['no result found']}))

    scheduler_post_result = {
        'form_is_valid': form_is_valid,
        'data': _dump_schedules_into_json(schedules),
        'interview_type': interview_template.type,
        'candidate_name': candidate_name,
        'interview_template_name': interview_template.template_name,
    }

    return HttpResponse(
        simplejson.dumps(scheduler_post_result),
        mimetype='application/json',
    )


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
