from django.http import HttpResponse
from django import forms
from django.shortcuts import render_to_response
from django.template import RequestContext

from jeeves import models

# TODO: Where does this go?
def all_reqs():
    return models.Requisition.objects.all()

def all_interviewers():
    return models.Interviewer.objects.all()

class FindTimesForm(forms.Form):
    requisition = forms.ModelChoiceField(queryset=all_reqs())

    start_time = forms.DateTimeField()
    end_time = forms.DateTimeField()

    also_include = forms.ModelMultipleChoiceField(
            queryset=all_interviewers(),
            required=False,
    )
    dont_include = forms.ModelMultipleChoiceField(
            queryset=all_interviewers(),
            required=False,
            label="Don't Include",
    )

def find_times(request):
    context = dict(
            find_times_form=FindTimesForm(),
    )

    return render_to_response('find_times.html', context, context_instance=RequestContext(request))

def find_times_post(request):
    # render_to_response(str_to_template, context_dict)
    context = dict(
            error_message="I can't find the times!",
    )

    return render_to_response('find_times.html', context)
