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

                   var roomInput = $('<input type="hidden" name="room">')
                   roomInput.val(schedule.room.interviewer);

                   var interviewerInput = $('<input type="hidden" name="interviewer">')
                   interviewerInput.val(slot.interviewer);

                   template.find('form').append(startTimeInput);
                   template.find('form').append(endTimeInput);
                   template.find('form').append(roomInput);
                   template.find('form').append(interviewerInput);
                 });


                 $('.schedule-list').append(template); 
               });
             }
        });
        event.preventDefault();
  });

});


