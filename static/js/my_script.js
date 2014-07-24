$(document).ready(function() {
  $( "#date-picker" ).datepicker();

  $("#scheduler_form").submit(function(event){
        $.ajax({
             type:"POST",
             url:"/new_scheduler_post/",
             data: $("#scheduler_form").serialize(),
             success: function(data){
               var schedules = data.data; 
               var interview_type = data.interview_type;
               var candidate_name = data.candidate_name;
               $.each(schedules, function(i, schedule) {
                 var template = $('#result .template').clone().removeClass('template'); 
                 template.find('.recruiter-select').addClass('chosen-select').chosen({max_selected_options:1});
                 var roomTime = schedule.room.start_time + ' ~ ' + schedule.room.end_time + ' ' + schedule.room.interviewer;

                 template.find('.room').text(roomTime);

                 var interview_type_input = $('<input type="hidden" name="interview_type">')
                 interview_type_input.val(interview_type);
                 template.find('form').append(interview_type_input);

                 var candidate_name_input = $('<input type="hidden" name="candidate_name">')
                 candidate_name_input.val(candidate_name);
                 template.find('form').append(candidate_name_input);

                 $.each(schedule.interview_slots, function(i, slot) {
                   var slotHtml = $('<p>' + slot.start_time + ' ' + slot.interviewer_name + '</p>');
                   template.find('.slots').append(slotHtml);
                   
                   var startTimeInput = $('<input type="hidden" name="start_time">')
                   startTimeInput.val(slot.start_datetime);
                   var endTimeInput = $('<input type="hidden" name="end_time">')
                   endTimeInput.val(slot.end_datetime);

                   var interviewerInput = $('<input type="hidden" name="interviewer">')
                   interviewerInput.val(slot.interviewer);

                   var roomInput = $('<input type="hidden" name="room">')
                   roomInput.val(schedule.room.interviewer);

                 var externalIdInput = $('<input type="hidden" name="external_id">')
                 externalIdInput.val(schedule.room.external_id);

                 var roomStartTimeInput = $('<input type="hidden" name="room_start_time">')
                 roomStartTimeInput.val(schedule.room.start_datetime);

                 var roomEndTimeInput = $('<input type="hidden" name="room_end_time">')
                 roomEndTimeInput.val(schedule.room.end_datetime);

                 template.find('form').append(roomInput);
                 template.find('form').append(roomStartTimeInput);
                 template.find('form').append(roomEndTimeInput);
                 template.find('form').append(externalIdInput);

                 var candidateNameInput = $('<input type="hidden" name="candidate_name">')
                 candidateNameInput.val($('input[name="candidate_name"]').val());
                 template.find('form').append(candidateNameInput);

                 var interviewTypeInput = $('<input type="hidden" name="interview_type">')
                 interviewTypeInput.val($('.type .chosen-select').val());
                 template.find('form').append(interviewTypeInput);

                 var requisitionInput = $('<input type="hidden" name="requisition">')
                 requisitionInput.val($('.req .chosen-select').val());
                 template.find('form').append(requisitionInput);

                   template.find('form').append(startTimeInput);
                   template.find('form').append(endTimeInput);
                   template.find('form').append(interviewerInput);
                 });


                 $('.schedule-list').append(template); 
               });
             }
        });
        event.preventDefault();
  });

});


