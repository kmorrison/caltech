from datetime import timedelta
import collections
import itertools
import random

from caltech import secret
from jeeves import models
from jeeves.calendar import lib
from jeeves.calendar.client import calendar_client

MINUTES_OF_INTERVIEW = 45
SCAN_RESOLUTION = 15  # Minutes

def calculate_schedules(required_interviewers, optional_interviewers, num_interviewers_needed, time_period, possible_break=None, max_schedules=20):
    num_attempts = 0
    accepted_schedules = []
    rooms = get_all_rooms(time_period)

    for possible_schedule in possible_schedules(
        required_interviewers, 
        optional_interviewers, 
        num_interviewers_needed, 
        time_period, 
        possible_break, 
        max_schedules
    ):

        # Add the schedule if it meets our validity heuristics
        if (is_valid_schedule(possible_schedule, rooms) 
        and possible_schedule not in accepted_schedules):
            accepted_schedules.append(possible_schedule)

        num_attempts += 1
        if num_attempts > 100000 or len(accepted_schedules) > max_schedules:
            print "exiting %s %s" % (num_attempts, len(accepted_schedules))
            break

    return accepted_schedules

InterviewSlot = collections.namedtuple('InterviewSlot', ('interviewer', 'start_time', 'end_time'))

def get_all_rooms(time_period):
    room_id = getattr(secret, 'room_id', None)
    if room_id is None:
        return None
    all_rooms = models.Requisition.objects.get(id=room_id).interviewers.all()
    return calendar_client.get_calendars([], all_rooms, time_period).interview_calendars

def possible_schedules(required_interviewers, optional_interviewers, num_interviewers_needed, time_period, possible_break, max_schedules):
    """A generator to generate a bunch of valid orders of interviewers whose times work.

    Does not take into account rooms, time padding, or previously generated interviews.
    """
    num_required = len(required_interviewers)
    assert num_required <= num_interviewers_needed, "Cannot require %s interviewers for only %s interviews" % (num_required, num_interviewers_needed)
    interviewer_pool = required_interviewers + [None for _ in xrange(num_interviewers_needed - num_required)]
    # Start with a random assortment of the required interviewers and empty space
    random.shuffle(interviewer_pool)

    for possible_order in itertools.permutations(interviewer_pool):
        for _ in xrange(1000):
            # For a random permutation of the required/empty set, sample some optional interviewers and try them out
            mutable_order = list(possible_order)
            chosen_optional = random.sample(optional_interviewers, num_interviewers_needed - num_required)
            none_indices = [i for i, element in enumerate(possible_order) if element is None]
            for replace_index, optional_interviewer in zip(none_indices, chosen_optional):
                # Fill in optional ones into space
                mutable_order[replace_index] = optional_interviewer

            if possible_break is not None:
                break_interview_slot = InterviewSlot('Break', possible_break.start_time, possible_break.end_time)

                # only try breaks in the first two interview slots
                for i in xrange(2):
                    order_with_break = list(mutable_order)
                    order_with_break.insert(i, break_interview_slot)
                    validated_order = try_order_with_anchor(order_with_break, anchor_index=i)
                    if validated_order is not None:
                        yield validated_order

            else:
                address_of_anchor = mutable_order[0].interviewer.address
                for possible_slot in possible_interview_chunks(mutable_order[0].free_times):
                    mutable_order[0] = InterviewSlot(address_of_anchor, possible_slot.start_time, possible_slot.end_time)

                    validated_order = try_order_with_anchor(mutable_order, anchor_index=0)
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
            required_slot = lib.time_period_of_length_after_time(anchor.start_time, MINUTES_OF_INTERVIEW, position - anchor_index)
        else:
            # Go forward n slots from end time
            required_slot = lib.time_period_of_length_after_time(anchor.end_time, MINUTES_OF_INTERVIEW, position - anchor_index - 1)

        if not interviewer.has_availability_during(required_slot):
            # This order won't work, return it as invalid
            return None
        interview_slots.append(InterviewSlot(interviewer.interviewer.address, required_slot.start_time, required_slot.end_time))
        
    return interview_slots


def is_valid_schedule(possible_schedule, rooms):
    if possible_schedule is None:
        return False

    if rooms is not None:
        # If we're looking at rooms, find one that fits and insert it into the schedule
        interview_duration = lib.TimePeriod(
            possible_schedule[0].start_time, 
            possible_schedule[-1].end_time
        )
        possible_rooms = [room for room in rooms if room.has_availability_during(interview_duration)]
        if not possible_rooms:
            return False

        # Choose a valid room randomly to avoid scheduling the same room always
        # because of arbitrary db ordering
        possible_schedule.append(InterviewSlot(
            random.choice(possible_rooms).interviewer.display_name, 
            interview_duration.start_time, 
            interview_duration.end_time
        ))

    return True


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
