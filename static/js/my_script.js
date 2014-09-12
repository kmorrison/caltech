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

                   var preference_table_html = $('<table class="preference_table">')
                   var table_header = $('<tr><th class="schedule-preference">Name</th><th class="schedule-preference">Meets Pref.</th><th class="schedule-preference">Buffer</th><th class="schedule-preference">Events</th></tr>')
                   template.find('.slots').append(preference_table_html);
                   preference_table_html.append(table_header);
                    // TODO: Rip out all this terrible js-making-html, it's driving me crazy
                   function pickme(val) {
                       if (val) {return "ui-icon ui-icon-plusthick"}
                       else {return "ui-icon ui-icon-minus"}
                   }
                 $.each(schedule.interview_slots, function(i, slot) {
                   var slotHtml = $('<tr><td>' + slot.start_time + ' ' + slot.interviewer_name + '</td>' + '<td><span class="' + pickme(slot.is_inside_time_preference) + '"></span></td><td><span class="' + pickme(slot.gets_buffer) + '"></span></td><td>' + slot.number_of_interviews + '</td></tr>');
                   preference_table_html.append(slotHtml);

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

                   template.find('form').append(startTimeInput);
                   template.find('form').append(endTimeInput);
                   template.find('form').append(interviewerInput);
                 });

                 template.find('#interview_template_input').val(data.interview_template_name);


                 $('.schedule-list').append(template); 
               });
             }
        });
        event.preventDefault();
  });

});


