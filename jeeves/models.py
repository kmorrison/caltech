#!/usr/bin/env python
# -*- coding: utf-8 -*-
from django.db import models
from django.contrib import admin

from datetime import datetime
import pytz
from caltech import settings


class Interview(models.Model):
    room = models.ForeignKey('Room')
    type = models.IntegerField()


class InterviewType(object):
    ON_SITE = 1
    SKYPE = 2

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


class Interviewer(models.Model):
    name = models.CharField(max_length=256)
    domain = models.CharField(max_length=256)
    display_name = models.CharField(max_length=256)
    interviews = models.ManyToManyField(Interview, through='Schedule')

    def __unicode__(self):
        return self.display_name

    @property
    def address(self):
        return "%s@%s" % (self.name, self.domain)

    class Meta:
        ordering = ('display_name',)


class Room(models.Model):
    name = models.CharField(max_length=256)
    domain = models.CharField(max_length=256)
    display_name = models.CharField(max_length=256)
    type = models.IntegerField()

    def __unicode__(self):
        return self.display_name

    @property
    def address(self):
        return "%s@%s" % (self.name, self.domain)

    class Meta:
        ordering = ('display_name',)


class Requisition(models.Model):
    name = models.CharField(max_length=256)
    interviewers = models.ManyToManyField(Interviewer, related_name='requisitions')

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ('name',)


class Schedule(models.Model):
    interview = models.ForeignKey(Interview)
    interviewer = models.ForeignKey(Interviewer)
    start_time = models.TimeField()
    end_time = models.TimeField()


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


admin.site.register(Interviewer, InterviewerAdmin)
admin.site.register(Requisition, RequisitionAdmin)
admin.site.register(Preference)
