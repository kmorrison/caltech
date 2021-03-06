#!/usr/bin/env python
# -*- coding: utf-8 -*-
from collections import namedtuple

from django.db import models
from django.contrib import admin
from django.contrib.auth.models import User

from datetime import datetime
import pytz
from caltech import settings

DEFAULT_MAX_INTERVIEWS = 3

class InterviewType(object):
    ON_SITE = 1
    SKYPE = 2
    SKYPE_ON_SITE = 4

    @classmethod
    def get_value(cls, *flags):
        result = 0
        for flag in flags:
            result |= flag
        return result

    @classmethod
    def are_flags_set(cls, type, *flags):
        value = cls.get_value(*flags)
        return value & type == value


class InterviewTypeChoice(object):

    def __init__(self, interview_type):
        self.interview_type = interview_type

    mapping = {
        InterviewType.ON_SITE: 'OS',
        InterviewType.SKYPE: 'SPI',
        InterviewType.SKYPE_ON_SITE: 'SOS',
    }

    reverse_mapping = dict([(v, k) for k, v in mapping.items()])

    @property
    def display_string(self):
        return self.mapping.get(self.interview_type)


class Interview(models.Model):
    candidate_name = models.CharField(max_length=256)
    room = models.ForeignKey('Room')
    type = models.IntegerField()
    time_created = models.DateTimeField(default=None, null=True, blank=True)
    google_event_id = models.CharField(max_length=256,
        default='',
        blank=True
    )
    recruiter = models.ForeignKey(
        'Recruiter',
        default=None,
        null=True,
        blank=True
    )
    user = models.ForeignKey(
        User,
        default=None,
        null=True,
        blank=True,
    )

    def __unicode__(self):
        return "%s - %s" % (InterviewTypeChoice.mapping.get(self.type, ''), self.candidate_name)

    class Meta:
        ordering = ('-time_created',)


class TimeChoice(object):
    # Use for display time purposes

  def __init__(self, time_value):
    self.time_value = time_value

  @property
  def display_string(self):
      hour_string = self.time_value[:2]
      if (int(hour_string)/12==0):
        hour = str(int(hour_string))
        period = 'am'
        if hour_string == '00':
          hour = '12'
      else:
        hour = str(int(hour_string) - 12)
        period = 'pm'
        if hour == '0':
          hour = '12'

      minute = self.time_value[3:5]
      return '{hour}:{minute} {period}'.format(hour=hour, minute=minute, period=period)


class Interviewer(models.Model):
    name = models.CharField(max_length=256)
    domain = models.CharField(max_length=256)
    display_name = models.CharField(max_length=256)
    interviews = models.ManyToManyField(Interview, through='InterviewSlot')

    preferences_address = models.CharField(max_length=256, null=True, blank=True)
    max_interviews_per_week = models.IntegerField(null=True)
    can_do_onsites = models.IntegerField(
        default=1,
        help_text='Type 1 if suitable for onsite, type 0 otherwise.'
    )

    @property
    def real_max_interviews(self):
        if self.max_interviews_per_week is None:
            return DEFAULT_MAX_INTERVIEWS
        return self.max_interviews_per_week

    def __unicode__(self):
        return self.display_name

    @property
    def address(self):
        return "%s@%s" % (self.name, self.domain)

    @property
    def external_id(self):
        return self.address

    class Meta:
        ordering = ('display_name',)


class AlternateRecruitingEventType(object):
    CODE_TEST = 1
    RESUME_SCREEN = 2


class AlternateRecruitingEvent(models.Model):
    interviewer = models.ForeignKey(Interviewer)
    type = models.IntegerField(
        choices=[
            (AlternateRecruitingEventType.CODE_TEST, "Code Test"),
            (AlternateRecruitingEventType.RESUME_SCREEN, "Resume Screen"),
        ],
    )
    time = models.DateTimeField()

    def __unicode__(self):
        return self.get_type_display()


class Room(models.Model):
    name = models.CharField(max_length=256)
    domain = models.CharField(max_length=256)
    display_name = models.CharField(max_length=256)

    type = models.IntegerField(
        help_text='Type 1 if suitable for onsite, type 0 otherwise.'
    )

    def __unicode__(self):
        return self.display_name

    @property
    def address(self):
        return "%s@%s" % (self.name, self.domain)

    @property
    def external_id(self):
        return self.address

    @property
    def is_suitable_for_onsite(self):
        return self.type == 1

    class Meta:
        ordering = ('display_name',)


InterviewerStruct = namedtuple('InterviewerStruct', ['address', 'external_id'])


class Requisition(models.Model):
    name = models.CharField(max_length=256)
    interviewers = models.ManyToManyField(Interviewer, related_name='requisitions')

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ('name',)


class InterviewTemplate(models.Model):
    requisition = models.ManyToManyField(
        Requisition,
        through='InterviewTemplateRequisition',
    )
    type = models.IntegerField(
        help_text="OS=%s, SPI=%s, SOS=%s" % (InterviewType.ON_SITE, InterviewType.SKYPE, InterviewType.SKYPE_ON_SITE),
    )
    template_name = models.CharField(max_length=256)

    def __unicode__(self):
        return self.template_name


class InterviewTemplateRequisition(models.Model):
    requisition = models.ForeignKey(Requisition)
    interview_template = models.ForeignKey(InterviewTemplate)
    number_per_requisition = models.IntegerField()


class InterviewSlot(models.Model):
    interview = models.ForeignKey(Interview)
    interviewer = models.ForeignKey(Interviewer)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()


DAYS_OF_WEEK = (
    ('0', 'Monday'),
    ('1', 'Tuesday'),
    ('2', 'Wednesday'),
    ('3', 'Thursday'),
    ('4', 'Friday'),
    ('5', 'Saturday'),
    ('6', 'Sunday'),
)


class Preference(models.Model):
    interviewer = models.ForeignKey('Interviewer')

    start_time = models.TimeField()
    end_time = models.TimeField()

    day = models.CharField(max_length=1, choices=DAYS_OF_WEEK)

    def __unicode__(self):
        return "%s: %s %s-%s" % (self.interviewer.display_name, self.get_day_display(), self.start_time, self.end_time)

    def time_period(self, date):
        from jeeves.calendar import lib
        preference_start_time = datetime(
            date.year, date.month, date.day, self.start_time.hour, self.start_time.minute, tzinfo=pytz.timezone(settings.TIME_ZONE)
        )
        preference_end_time = datetime(
            date.year, date.month, date.day, self.end_time.hour, self.end_time.minute, tzinfo=pytz.timezone(settings.TIME_ZONE)
        )
        return lib.TimePeriod(preference_start_time, preference_end_time)


class Recruiter(models.Model):
    name = models.CharField(max_length=256)
    domain = models.CharField(max_length=256)
    display_name = models.CharField(max_length=256)

    def __unicode__(self):
        return self.display_name

    @property
    def address(self):
        return "%s@%s" % (self.name, self.domain)

    @property
    def external_id(self):
        return self.address

    class Meta:
        ordering = ('display_name',)


class RequisitionInline(admin.TabularInline):
    model = Requisition.interviewers.through


class PreferenceInline(admin.TabularInline):
    model = Preference


class InterviewerAdmin(admin.ModelAdmin):
    inlines = [RequisitionInline, PreferenceInline]


class RequisitionAdmin(admin.ModelAdmin):
    inlines = [RequisitionInline]
    exclude = ('interviewers',)


class PreferenceAdmin(admin.ModelAdmin):
    list_display = ['interviewer']


class InterviewTemplateInline(admin.TabularInline):
    model = InterviewTemplate.requisition.through


class InterviewTemplateAdmin(admin.ModelAdmin):
    inlines = [InterviewTemplateInline]


admin.site.register(Interviewer, InterviewerAdmin)
admin.site.register(Interview)
admin.site.register(Requisition, RequisitionAdmin)
admin.site.register(InterviewTemplate, InterviewTemplateAdmin)
admin.site.register(AlternateRecruitingEvent)
admin.site.register(Preference)
admin.site.register(Room)
admin.site.register(InterviewSlot)
admin.site.register(Recruiter)
