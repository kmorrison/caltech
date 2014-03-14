from jeeves import models
from jeeves.models import InterviewType


INTERVIEW_MAPPING_RULES = {
        'Backend':{
            InterviewType.ON_SITE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE: [(2, 'Backend'), (0, 'Stoppelgangers')],
            InterviewType.SKYPE_ON_SITE: [(1, 'Backend'), (1, 'Stoppelgangers')],
            },
        'Ads':{
            InterviewType.ON_SITE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE_ON_SITE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            },
        'Engineer Manager':{
            InterviewType.ON_SITE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE_ON_SITE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            },
        'Search':{
            InterviewType.ON_SITE: [(2, 'Search'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE_ON_SITE: [(2, 'Search'), (2, 'Stoppelgangers')],
            },
        'Spam':{
            InterviewType.ON_SITE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE_ON_SITE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            },
        'Data Scientist':{
            InterviewType.ON_SITE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE_ON_SITE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            },
        'Web Dev':{
            InterviewType.ON_SITE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE_ON_SITE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            },
        'Infra':{
            InterviewType.ON_SITE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE_ON_SITE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            },
        'Sys Infra':{
            InterviewType.ON_SITE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE_ON_SITE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            },
        'Data Scientist':{
            InterviewType.ON_SITE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE_ON_SITE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            },
        'Web Dev':{
            InterviewType.ON_SITE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE_ON_SITE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            },
        'Infra':{
            InterviewType.ON_SITE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE_ON_SITE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            },
        'Sys Infra':{
            InterviewType.ON_SITE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE_ON_SITE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            },
        'Mobile':{
            InterviewType.ON_SITE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE_ON_SITE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            },
        'Sys Admin (Corp)':{
            InterviewType.ON_SITE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE_ON_SITE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            },
        'MySQL DBA':{
            InterviewType.ON_SITE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE_ON_SITE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            },
        'New Grad/Intern':{
            InterviewType.ON_SITE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE_ON_SITE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            },
        'PM':{
            InterviewType.ON_SITE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE_ON_SITE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            },
        'IT HelpDesk Manager':{
            InterviewType.ON_SITE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE_ON_SITE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            },
        'Front End':{
            InterviewType.ON_SITE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE_ON_SITE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            },
        'Engineering Manager - Security':{
            InterviewType.ON_SITE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE_ON_SITE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            },
        'Sys Admin (Prod)':{
            InterviewType.ON_SITE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE_ON_SITE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            },
        'Stoppelgangers':{
            InterviewType.ON_SITE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE_ON_SITE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            },
        'Search/ads/spam':{
            InterviewType.ON_SITE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            InterviewType.SKYPE_ON_SITE: [(2, 'Backend'), (2, 'Stoppelgangers')],
            },
        }


def get_interview_requirements(requisition, interview_type):
    req_rules = INTERVIEW_MAPPING_RULES.get(requisition.name)

    if not req_rules:
        return None

    return req_rules.get(interview_type)

def get_interview_group(rule):
    result = []
    for number, req_name in rule:
        req = models.Requisition.objects.filter(name__startswith=req_name)[0]
        result.append([number, set(req.interviewers.all())])
    return result
