from django.shortcuts import render_to_response
from django.http import HttpResponse

def find_times(request):
    # render_to_response(str_to_template, context_dict)
    context = dict(
            error_message="I can't find the times!",
    )

    return render_to_response('find_times.html', context)
