from datetime import timedelta
import collections
import itertools
import random
import time

from caltech import secret
from jeeves import models
from jeeves.calendar import lib
from jeeves.calendar.client import calendar_client

MINUTES_OF_INTERVIEW = 45
SCAN_RESOLUTION = 15  # Minutes
IDEAL_PADDING_TIME = 15  # Minutes
BREAK = 'Break'


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
    ):
        self.interviewer = interviewer
        self.start_time = start_time
        self.end_time = end_time

        self.is_inside_time_preference = is_inside_time_preference
        self.gets_buffer = gets_buffer
        self.number_of_interviews = number_of_interviews

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
    
    

Interview = collections.namedtuple('Interview', ('interview_slots', 'room', 'priority'))
InterviewerGroup = collections.namedtuple('InterviewerGroup', ('num_required', 'interviewers'))


def calculate_schedules(interviewer_groups, time_period, possible_break=None, max_schedules=100):
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
    preferences = get_preferences(interviewers)

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

    return sorted(created_interviews, key=lambda x: x.priority, reverse=True)[:20]

def get_all_rooms(time_period):
    all_rooms = models.Room.objects.all()
    return calendar_client.get_calendars(all_rooms, time_period).interview_calendars

def get_preferences(interviewers):
    # WARNING: N DB queries
    return dict(
            (interviewer.interviewer.address, interviewer.interviewer.preference_set.all())
            for interviewer in interviewers
    )

def generate_possible_orders_forever(interviewer_groups):
    """Given a grouping of interviews, generate possible schedules."""
    while True:
        possible_order = []
        for interviewer_group in interviewer_groups:
            possible_order.extend(random.sample(interviewer_group.interviewers, interviewer_group.num_required))
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
                if validated_order is not None:
                    yield validated_order

        else:
            address_of_anchor = possible_order[0].interviewer.address
            for possible_slot in possible_interview_chunks(possible_order[0].free_times):
                possible_order[0] = InterviewSlot(
                    interviewer=address_of_anchor,
                    start_time=possible_slot.start_time,
                    end_time=possible_slot.end_time,
                )

                validated_order = try_order_with_anchor(possible_order, anchor_index=0)
                if validated_order is not None:
                    yield validated_order


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
            )
        )

    return interview_slots

def calculate_preference_scores(interview_slots, preferences):
    return [
        _preference_score(interview_slot, preferences.get(interview_slot.interviewer))
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


def _preference_score(interviewer_slot, preferences):
    if interviewer_slot.interviewer == BREAK:
        return 10

    if not preferences:
        return 10

    assert interviewer_slot.start_time.date() == interviewer_slot.end_time.date()
    date = interviewer_slot.start_time.date()

    for preference in preferences:
        if preference.day != str(interviewer_slot.start_time.weekday()):
            continue

        if preference.time_period(date).contains(
            lib.TimePeriod(interviewer_slot.start_time, interviewer_slot.end_time)
        ):
            return 15

    return 0


def create_interview(possible_schedule, interviewers, rooms, preferences):
    if possible_schedule is None:
        return None

    room = None
    room_score = 0
    if rooms is not None:
        # If we're looking at rooms, find one that fits and insert it into the schedule
        interview_duration = lib.TimePeriod(
            possible_schedule[0].start_time,
            possible_schedule[-1].end_time
        )
        possible_rooms = [room for room in rooms if room.has_availability_during(interview_duration)]
        if possible_rooms:
            # Choose a valid room randomly to avoid scheduling the same room always
            # because of arbitrary db ordering
            room = InterviewSlot(
                random.choice(possible_rooms).interviewer.display_name,
                interview_duration.start_time,
                interview_duration.end_time
            )
            room_score = 100

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

    # TODO: Calculate priority based on interview padding
    return Interview(
        interview_slots=possible_schedule,
        room=room,
        priority=(
            room_score
            + preference_score
            + interviewer_schedule_padding_score
        )
    )


def possible_interview_chunks(free_times):
    """Given a list of free times, yield them in 45 minute chunks."""
    possible_free_times = filter_free_times_for_length(free_times)

    for free_time in possible_free_times:
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
