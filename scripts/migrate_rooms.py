from jeeves import models

def migrate_rooms(room_req_id):
    room_interviewers = models.Requisition.objects.get(
        id=room_req_id
    ).interviewers.all()

    for room_interviewer in room_interviewers:
        models.Room.objects.create(
            name=room_interviewer.name,
            domain=room_interviewer.domain,
            display_name=room_interviewer.display_name,
            type=models.InterviewType.ON_SITE
        )
        room_interviewer.delete()
