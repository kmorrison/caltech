from django.http import HttpResponse

def find_times(request):
    # render_to_response(str_to_template, context_dict)
    return HttpResponse("Hello world")
