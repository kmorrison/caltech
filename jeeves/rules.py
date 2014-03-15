from jeeves import models
from jeeves.models import InterviewType
from caltech import secret

default_rules = {
    InterviewType.ON_SITE: [(2, 'Backend'), (2, 'Stoppelgangers')],
    InterviewType.SKYPE: [(1, 'Backend')],
    InterviewType.SKYPE_ON_SITE: [(2, 'Backend')],
}

# THIS NEEDS TO BE SET
interview_mapping_rules = getattr(secret, 'interview_mapping_rules', None)


def get_interview_requirements(requisition, interview_type):
    if interview_mapping_rules is None:
        req_rules = default_rules
    else:
        req_rules = interview_mapping_rules.get(requisition.name)

    if not req_rules:
        return None

    return req_rules.get(interview_type)


def get_interview_group(rule):
    result = []
    for number, req_name in rule:
        req = models.Requisition.objects.filter(name__startswith=req_name)[0]
        result.append([number, set(req.interviewers.all())])
    return result
