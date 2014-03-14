from jeeves import models
from jeeves.models import InterviewType


INTERVIEW_MAPPING_RULES = {
        'Backend':{
            InterviewType.ON_SITE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            },
        'Ads':{
            InterviewType.ON_SITE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            },
        'Engineer Manager':{
            InterviewType.ON_SITE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            },
        'Search':{
            InterviewType.ON_SITE: [(2, 'Search'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE: [(2, 'Search'), (2, 'Stoppelgangers')],
            },
        'Spam':{
            InterviewType.ON_SITE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            },
        'Data Scientist':{},
        'Web Dev':{},
        'Infra':{},
        'Sys Infra':{},
        }


def get_interviewers(requisition):
    req_rules = INTERVIEW_MAPPING_RULES.get(requisition.name)

    if not req_rules:
        return None

    interviewers = {}
    for interview_type, rules in req_rules.iteritems():
        interviewer_selection = {}
        for number, req_name in rules:
            req = models.Requisition.objects.filter(name__startswith=req_name)[0]
            interviewer_selection[req.name] = req.interviewers.all()
        interviewers[interview_type] = interviewer_selection

    return interviewers
