import datetime
from datetime import timedelta
import collections
import heapq
import itertools
import random
import time
import pytz


from caltech import secret
from jeeves import models
from jeeves.calendar import lib
from jeeves.calendar.client import calendar_client

MINUTES_OF_INTERVIEW = 45
SCAN_RESOLUTION = 15  # Minutes
IDEAL_PADDING_TIME = 15  # Minutes
BREAK = 'Break'


class NoInterviewersAvailableError(Exception): pass


class InterviewSlot(object):
    """Object representing an interviewer doing an interview at a certain time."""
    def __init__(
        self,
        interviewer,
        start_time,
        end_time,

        is_inside_time_preference=False,
        gets_buffer=False,
        number_of_interviews='n/a',
        external_id=None,
        interviewer_name="",
    ):
        self.interviewer = interviewer
        self.interviewer_name = interviewer_name
        self.start_time = start_time
        self.end_time = end_time

        self.is_inside_time_preference = is_inside_time_preference
        self.gets_buffer = gets_buffer
        self.number_of_interviews = number_of_interviews
        self.external_id = external_id

    @property
    def display_time(self):
        time_format = "%I:%M"
        return "%s - %s" % (self.start_time.strftime(time_format), self.end_time.strftime(time_format))

    @property
    def display_start_time(self):
        return self.start_time.strftime("%I:%M")

    @property
    def display_end_time(self):
        return self.end_time.strftime("%I:%M")

    @property
    def display_date(self):
        return self.start_time.date().strftime("%x")

    @property
    def start_datetime(self):
        return time.mktime(self.start_time.timetuple())

    @property
    def end_datetime(self):
        return time.mktime(self.end_time.timetuple())


class Interview(object):
    def __init__(self, interview_slots, room, priority):
        self.interview_slots = interview_slots
        self.room = room
        self.priority = priority
InterviewerGroup = collections.namedtuple('InterviewerGroup', ('num_required', 'interviewers'))


def load_number_of_alternate_events(interviewer_id, week_start, week_end):
    alternative_events = models.AlternateRecruitingEvent.objects.filter(
        interviewer_id=interviewer_id,
    )
    number_of_events_in_the_week = 0
    for event in alternative_events:
        week = event.time.date().isocalendar()[1]
        if week_start == week:
            number_of_events_in_the_week += 1

    return number_of_events_in_the_week


def _prune_interviewers_for_capacity(interviewers, time_period):
    week_start = time_period.start_time.date().isocalendar()[1]
    week_end = time_period.end_time.date().isocalendar()[1]
    assert week_start == week_end
    pruned_interviewers = {}
    for interviewer in interviewers:
        interview_slots = interviewer.interviewer.interviewslot_set.all()
        interviews = 0
        for interview_slot in interview_slots:
            week = interview_slot.start_time.date().isocalendar()[1]
            if week == week_start:
                interviews += 1

        if interviewer.interviewer.real_max_interviews is None:
            raise ValueError("Max interviews cannot be None, call an engineer")
        number_of_alternate_events = load_number_of_alternate_events(
            interviewer.interviewer.id,
            week_start,
            week_end,
        )
        if interviews < interviewer.interviewer.real_max_interviews:
            pruned_interviewers[interviewer.interviewer.address] = (interviewer, interviews + number_of_alternate_events)

    return pruned_interviewers


def _prune_interviewers_for_onsite_ability(interviewers, interview_type):
    if interview_type == models.InterviewType.ON_SITE:
        return [interviewer for interviewer in interviewers if interviewer.interviewer.can_do_onsites]
    return interviewers


def _prune_overcapacity_interviewers_from_groups(interviewer_groups, interviewers):
    interviewer_set = set([interviewer.interviewer.address for interviewer in interviewers])
    pruned_interviewer_groups = []
    for interviewer_group in interviewer_groups:
        igroup_interviewers = interviewer_group.interviewers
        igroup_interviewers = [interviewer for interviewer in igroup_interviewers if interviewer.interviewer.address in interviewer_set]
        if len(igroup_interviewers) < interviewer_group.num_required:
            raise NoInterviewersAvailableError
        pruned_interviewer_groups.append(InterviewerGroup(num_required=interviewer_group.num_required, interviewers=igroup_interviewers))
    return pruned_interviewer_groups

def calculate_schedules(
    interviewer_groups,
    time_period,
    possible_break=None,
    max_schedules=150,
    interview_type=None
):
    """Exposed method for calculating new interviews.

    Returns:
      List of <Interview>s
    """
    num_attempts = 0
    created_interviews = []
    rooms = get_all_rooms(time_period)
    interviewers = list(itertools.chain.from_iterable(
        interviewer_group.interviewers for interviewer_group in interviewer_groups
    ))
    interviewers = _prune_interviewers_for_onsite_ability(interviewers, interview_type)
    interviewer_to_num_interviews_map = _prune_interviewers_for_capacity(interviewers, time_period)
    if not interviewer_to_num_interviews_map:
        raise NoInterviewersAvailableError
    interviewers = zip(*interviewer_to_num_interviews_map.values())[0]
    interviewer_groups = _prune_overcapacity_interviewers_from_groups(interviewer_groups, interviewers)
    preferences = get_preferences(interviewers, time_period)

    for possible_schedule in possible_schedules(
        interviewer_groups,
        time_period,
        possible_break,
        max_schedules
    ):

        interview = create_interview(
            possible_schedule,
            interviewers,
            rooms,
            preferences,
            interviewer_to_num_interviews_map,
            interview_type=interview_type
        )

        # Add the schedule if it meets our validity heuristics
        if (
            interview is not None
            and interview not in created_interviews
        ):
            created_interviews.append(interview)

        num_attempts += 1
        if num_attempts > 100000 or len(created_interviews) > max_schedules:
            print "exiting %s %s" % (num_attempts, len(created_interviews))
            break

    return sorted(created_interviews, key=lambda x: (-1 * x.priority, x.room.start_time))

def get_all_rooms(time_period):
    all_rooms = models.Room.objects.all()
    return calendar_client.get_calendars(all_rooms, time_period).interview_calendars

def get_preferences(interviewers, time_period):
    preferences = calendar_client.get_calendars(
        [
            models.InterviewerStruct(
                external_id=interviewer.interviewer.preferences_address,
                address=interviewer.interviewer.address
            )
            for interviewer in interviewers
        ],
        time_period,
    )
    return preferences


def has_same_interviewer_twice(possible_order):
    interviewer_ids = set([interviewer.interviewer.id for interviewer in possible_order])
    return len(interviewer_ids) != len(possible_order)


def generate_possible_orders_forever(interviewer_groups):
    """Given a grouping of interviews, generate possible schedules."""
    while True:
        possible_order = []
        for interviewer_group in interviewer_groups:
            possible_order.extend(random.sample(interviewer_group.interviewers, interviewer_group.num_required))
        if has_same_interviewer_twice(possible_order):
            continue
        yield possible_order


def possible_schedules(interviewer_groups, time_period, possible_break, max_schedules):
    """A generator to generate a bunch of valid orders of interviewers whose times work.

    Does not take into account rooms, time padding, or previously generated interviews.
    """
    for iteration, possible_order in enumerate(generate_possible_orders_forever(interviewer_groups)):
        possible_order = list(possible_order)

        if possible_break is not None:
            break_interview_slot = InterviewSlot(
                interviewer=BREAK,
                start_time=possible_break.start_time,
                end_time=possible_break.end_time,
            )

            # only try breaks in the first two interview slots
            for i in xrange(2):
                order_with_break = list(possible_order)
                order_with_break.insert(i, break_interview_slot)
                validated_order = try_order_with_anchor(order_with_break, anchor_index=i)
                if validated_order is not None and _validate_interview_times(validated_order, time_period):
                    yield validated_order

        else:
            address_of_anchor = possible_order[0].interviewer.address
            name_of_anchor = possible_order[0].interviewer.display_name
            for possible_slot in possible_interview_chunks(possible_order[0].free_times):
                possible_order[0] = InterviewSlot(
                    interviewer=address_of_anchor,
                    start_time=possible_slot.start_time,
                    end_time=possible_slot.end_time,
                    interviewer_name=name_of_anchor
                )

                validated_order = try_order_with_anchor(possible_order, anchor_index=0)
                if validated_order is not None and _validate_interview_times(validated_order, time_period):
                    yield validated_order


def _validate_interview_times(validated_order, time_period):
    if validated_order[0].start_time < time_period.start_time:
        return False
    if validated_order[-1].end_time > time_period.end_time:
        return False
    return True


def try_order_with_anchor(possible_order, anchor_index):
    """Given a random order with an anchor that his its times filled already, see if the rest of the times would make sense.

    Replace interviewers in the possible order with InterviewSlots, which are interviewers with associated times.
    """
    interview_slots = []
    anchor = possible_order[anchor_index]
    for position, interviewer in enumerate(possible_order):

        if position == anchor_index:
            interview_slots.append(interviewer)
            continue
        if interviewer is None:
            continue

        if position < anchor_index:
            # Go back n slots from start time
            required_slot = lib.time_period_of_length_after_time(
                anchor.start_time,
                MINUTES_OF_INTERVIEW,
                position - anchor_index
            )
        else:
            # Go forward n slots from end time
            required_slot = lib.time_period_of_length_after_time(
                anchor.end_time,
                MINUTES_OF_INTERVIEW,
                position - anchor_index - 1
            )

        if not interviewer.has_availability_during(required_slot):
            # This order won't work, return it as invalid
            return None
        interview_slots.append(
            InterviewSlot(
                interviewer=interviewer.interviewer.address,
                start_time=required_slot.start_time,
                end_time=required_slot.end_time,
                interviewer_name=interviewer.interviewer.display_name,
            )
        )

    return interview_slots


def calculate_preference_scores(interview_slots, preference_calendars):
    return [
        _preference_score(
            interview_slot,
            preference_calendars.get_interviewer(interview_slot.interviewer),
        )
        for interview_slot in interview_slots
    ]


def calculate_interviewer_schedule_padding_scores(possible_schedule, interviewer_calendars):
    interviewer_by_address = dict(
        (interviewer_calendar.interviewer.address, interviewer_calendar)
        for interviewer_calendar in interviewer_calendars
    )

    padding_scores = []
    for interviewer_slot in possible_schedule:
        if interviewer_slot.interviewer == BREAK:
            padding_scores.append(5)
            continue

        interviewer_calendar = interviewer_by_address[interviewer_slot.interviewer]
        interviewer_time_with_padding = lib.TimePeriod(
            interviewer_slot.start_time,
            interviewer_slot.end_time + timedelta(minutes=IDEAL_PADDING_TIME)
        )

        if interviewer_calendar.has_availability_during(interviewer_time_with_padding):
            padding_scores.append(5)
        else:
            padding_scores.append(0)

    return padding_scores


def _preference_score(interviewer_slot, preferences_calendar):
    if interviewer_slot.interviewer == BREAK:
        return 10

    if not preferences_calendar:
        return 0

    assert interviewer_slot.start_time.date() == interviewer_slot.end_time.date()

    if preferences_calendar.is_blocked_during(lib.TimePeriod(interviewer_slot.start_time, interviewer_slot.end_time)):
        return 30
    return 0


def create_interview(possible_schedule, interviewers, rooms, preferences, interviewer_to_num_interviews_map, interview_type=None):
    if possible_schedule is None:
        return None

    chosen_room = None
    room_score = 0
    if rooms is not None:
        # If we're looking at rooms, find one that fits and insert it into the schedule
        interview_duration = lib.TimePeriod(
            possible_schedule[0].start_time,
            possible_schedule[-1].end_time
        )
        possible_rooms = [room for room in rooms if room.has_availability_during(interview_duration)]
        if possible_rooms:
            onsite_rooms = [room for room in possible_rooms if room.interviewer.is_suitable_for_onsite]
            if interview_type == models.InterviewType.ON_SITE and onsite_rooms:
                possible_rooms = onsite_rooms

            # Choose a valid room randomly to avoid scheduling the same room always
            # because of arbitrary db ordering
            random_room = random.choice(possible_rooms)
            chosen_room = InterviewSlot(
                random_room.interviewer.display_name,
                interview_duration.start_time,
                interview_duration.end_time,
                external_id=random_room.interviewer.external_id,
            )
            room_score = 150

            if interview_type == models.InterviewType.ON_SITE:
                if not random_room.interviewer.is_suitable_for_onsite:
                    room_score -= 50


    preference_scores = calculate_preference_scores(possible_schedule, preferences)
    preference_score = sum(preference_scores)
    for interview_slot, score in zip(possible_schedule, preference_scores):
        interview_slot.is_inside_time_preference = bool(score)

    interviewer_schedule_padding_scores = calculate_interviewer_schedule_padding_scores(
          possible_schedule,
          interviewers,
    )
    interviewer_schedule_padding_score = sum(interviewer_schedule_padding_scores)
    for interview_slot, score in zip(possible_schedule, interviewer_schedule_padding_scores):
        interview_slot.gets_buffer = bool(score)

    num_interviews_score = 50
    for interview_slot in possible_schedule:
        num_interviews = interviewer_to_num_interviews_map.get(interview_slot.interviewer, (None, 0))[1]
        num_interviews_score -= (5 * num_interviews)
        interview_slot.number_of_interviews = num_interviews

    slots_to_store = [islot for islot in possible_schedule if islot.interviewer != BREAK]


    return Interview(
        interview_slots=slots_to_store,
        room=chosen_room,
        priority=(
            room_score
            + preference_score
            + interviewer_schedule_padding_score
            + num_interviews_score
        )
    )


def possible_interview_chunks(free_times):
    """Given a list of free times, yield them in 45 minute chunks."""
    possible_free_times = filter_free_times_for_length(free_times)

    for free_time in free_times:
        potential_time = lib.TimePeriod(free_time.start_time, free_time.start_time + timedelta(minutes=MINUTES_OF_INTERVIEW))
        while potential_time.end_time < free_time.end_time:

            # Only schedule interviews at minute multiples of the scan
            # resolution. IE., if the resolution is 15 minutes, only consider
            # interviews at 11:00, 11:15, 11:30
            if potential_time.end_time.minute % SCAN_RESOLUTION == 0:
                assert potential_time.start_time.minute % SCAN_RESOLUTION == 0
                yield potential_time

            potential_time = lib.TimePeriod(
                    potential_time.start_time + timedelta(minutes=SCAN_RESOLUTION),
                    potential_time.end_time + timedelta(minutes=SCAN_RESOLUTION),
            )


def filter_free_times_for_length(free_times):
    """Given a list of free times, return chunks that are of the given length or greater."""
    return [free_time for free_time in free_times if free_time.length_in_minutes >= MINUTES_OF_INTERVIEW]


def persist_interview(interview_infos, interview_type, recruiter_id=None, google_event_id='', user_id=None):
    interview_info = interview_infos[0]
    room_id = interview_info['room_id']
    candidate_name = interview_info['candidate_name']

    now = datetime.datetime.now()
    interview = models.Interview.objects.create(
        candidate_name=candidate_name,
        room_id=room_id,
        recruiter_id=recruiter_id,
        type=interview_type,
        google_event_id=google_event_id,
        user_id=user_id,
        time_created=now,
    )

    for interview_info in interview_infos:
        assert interview_info['room_id'] == room_id
        models.InterviewSlot.objects.create(
            interview_id=interview.id,
            interviewer_id=interview_info['interviewer_id'],
            start_time=interview_info['start_time'],
            end_time=interview_info['end_time']
        )

    return interview.id


def get_interviews(start_time, end_time):
    getter = _InterviewGetter(start_time, end_time)
    return getter.get()


class _InterviewGetter(object):

    def __init__(self, start_time, end_time):
        self._start_time = start_time
        self._end_time = end_time

    def get(self):
        interview_slots = self._get_interview_slots()
        output = {}
        for interview_slot in interview_slots:
            interviews_data = {
                'room': interview_slot.interview.room.display_name,
                'start_time': interview_slot.start_time,
                'end_time': interview_slot.end_time,
                'candidate_name': interview_slot.interview.candidate_name,
                'day_of_week': interview_slot.start_time.weekday(),
                'interview_id': interview_slot.interview.id,
                'interview_slot_id': interview_slot.id,
                'interview_type': models.InterviewTypeChoice(interview_slot.interview.type).display_string,
            }

            for req in interview_slot.interviewer.requisitions.all():
                output.setdefault(req.name, {})
                req_interviewers = output[req.name]
                req_interviewers.setdefault(
                    interview_slot.interviewer.display_name,
                    []
                )
                req_interviewer_slots = \
                    req_interviewers[interview_slot.interviewer.display_name]

                req_interviewer_slots.append(
                    interviews_data.copy()
                )

        return output

    def _get_interview_slots(self):
        return models.InterviewSlot.objects.filter(
            start_time__gte=self._start_time,
            end_time__lte=self._end_time,
        )


def get_all_req_to_interviewers():
    reqs = models.Requisition.objects.all()
    req_to_interviewers_map = {}

    for req in reqs:
        req_to_interviewers_map[req.name] = [
            interviewer.display_name for interviewer in req.interviewers.all()
        ]

    return req_to_interviewers_map


def get_interviews_with_all_interviewers(*args, **kwargs):
    interviews = get_interviews(*args, **kwargs)
    req_to_interviewers = get_all_req_to_interviewers()

    for req, interviewers in req_to_interviewers.iteritems():
        interviews.setdefault(req, {})

        for interviewer in interviewers:
            interviews[req].setdefault(interviewer, [])

    return interviews

def create_calendar_body(time_name_pairs, recruiter, user):
    list_of_interviewers = []

    for time, name in time_name_pairs:
        list_of_interviewers.append(
            '%(time)s: %(name)s' % {
                'time': time.timetz().strftime("%I:%M"),
                'name': name,
            },
        )
    body = '\n'.join(list_of_interviewers)

    body += '\nRecruiter: %s (%s@%s)' % (recruiter.display_name, recruiter.name, recruiter.domain)
    body += '\nScheduler by: %s' % (user.username,)

    return body


def change_interviewer(interview_slot_id, interviewer_id):
    slot = models.InterviewSlot.objects.get(id=interview_slot_id)
    slot.interviewer_id = interviewer_id
    google_event_id = slot.interview.google_event_id
    slot.save()
    if google_event_id:
        updated_description_list = []
        new_description = create_calendar_body(
            [(
                interview_slot.start_time.astimezone(pytz.timezone('US/Pacific')),
                interview_slot.interviewer.name)
                for interview_slot in slot.interview.interviewslot_set.all()
            ],
            slot.interview.recruiter,
            slot.interview.user,
        )
        calendar_response = calendar_client.update_event(google_event_id, new_description)



def delete_interview(interview_id):
    interview = models.Interview.objects.get(id=interview_id)
    for slot in interview.interviewslot_set.all():
        slot.delete()
    interview.delete()
    google_event_id = interview.google_event_id
    if google_event_id:
        calendar_response = calendar_client.delete_event(google_event_id)


def get_all_recruiters():
    return models.Recruiter.objects.all()
