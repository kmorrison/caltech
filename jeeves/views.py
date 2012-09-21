from datetime import timedelta

from django.http import HttpResponse
from django import forms
from django.shortcuts import render
from django.shortcuts import render_to_response
from django.template import RequestContext

from jeeves import models
from jeeves.calendar.client import calendar_client
from jeeves.calendar.lib import TimePeriod

# TODO: Clearly the wrong place for this
TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

# TODO: Where does this go?
def all_reqs():
    return models.Requisition.objects.all()

def all_interviewers():
    return models.Interviewer.objects.all()

def get_interviewers(requisition, also_include=None, dont_include=None):
    requisition = models.Requisition.objects.get(id=requisition.id)
    interviewers = set(requisition.interviewers.all())

    if also_include is not None:
        interviewers.update(models.Interviewer.objects.filter(id__in=[i.id for i in also_include]))

    if dont_include is not None:
        interviewers -= set(models.Interviewer.objects.filter(id__in=[i.id for i in dont_include]))

    return interviewers

class FindTimesForm(forms.Form):
    requisition = forms.ModelChoiceField(queryset=all_reqs())

    start_time = forms.DateTimeField()
    end_time = forms.DateTimeField()

    also_include = forms.ModelMultipleChoiceField(
            queryset=all_interviewers(),
            required=False,
            widget=forms.widgets.CheckboxSelectMultiple,
    )
    dont_include = forms.ModelMultipleChoiceField(
            queryset=all_interviewers(),
            required=False,
            widget=forms.widgets.CheckboxSelectMultiple,
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


def find_times(request):
    context = dict(
            find_times_form=FindTimesForm(),
    )

    return render_to_response('find_times.html', context, context_instance=RequestContext(request))

def find_times_post(request):
    find_times_form = FindTimesForm(request.POST)
    if find_times_form.is_valid():
        interviewers = get_interviewers(
                *find_times_form.requisition_and_custom_interviewers
        )

        calendar_response = calendar_client.get_calendars(interviewers, find_times_form.time_period)

        return render(
                request,
                'find_times.html',
                dict(
                    find_times_form=find_times_form,
                    calendar_response=calendar_response,
                )
        )

