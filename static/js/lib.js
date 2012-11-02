$(function() {
        
		var startDateTextBox = $('#id_start_time');
		var endDateTextBox = $('#id_end_time');
		
		var startBreakTextBox = $('#id_break_start_time');
		var endBreakTextBox = $('#id_break_end_time');
		
		var datePickerStartPrefs = {
		
			dateFormat: "yy-mm-dd", 
			timeFormat: "hh:mm:ss",			
			beforeShowDay: $.datepicker.noWeekends,
			showHour: true,
			hourMin: 9,
			hourMax: 19,
			hourGrid: 1,
			showMinute: true,
			minuteGrid: 15,
			stepMinute: 15,
	
			
			onClose: function(dateText, inst) {
				if (endDateTextBox.val() != '') {
					var testStartDate = startDateTextBox.datetimepicker('getDate');
					var testEndDate = endDateTextBox.datetimepicker('getDate');
					if (testStartDate > testEndDate)
						endDateTextBox.datetimepicker('setDate', testStartDate);
				}
				else {
					endDateTextBox.val(dateText);
				}
			},
			
			onSelect: function (selectedDateTime){
				endDateTextBox.datetimepicker('option', 'minDate', startDateTextBox.datetimepicker('getDate') );
			}
		};
		
		var datePickerEndPrefs = { 
			
			dateFormat: "yy-mm-dd", 
			timeFormat: "hh:mm:ss",			
			beforeShowDay: $.datepicker.noWeekends,
			showHour: true,
			hourMin: 9,
			hourMax: 19,
			hourGrid: 1,
			showMinute: true,
			minuteGrid: 15,
			stepMinute: 15,
			
			onClose: function(dateText, inst) {
				if (startDateTextBox.val() != '') {
					var testStartDate = startDateTextBox.datetimepicker('getDate');
					var testEndDate = endDateTextBox.datetimepicker('getDate');
					if (testStartDate > testEndDate)
						startDateTextBox.datetimepicker('setDate', testEndDate);
				}
				else {
					startDateTextBox.val(dateText);
				}
			},
			
			onSelect: function (selectedDateTime){
				startDateTextBox.datetimepicker('option', 'maxDate', endDateTextBox.datetimepicker('getDate') );
			}
		};

		var datePickerBreakPrefs = {
		
			dateFormat: "yy-mm-dd", 
			timeFormat: "hh:mm:ss",			
			beforeShowDay: $.datepicker.noWeekends,
			showHour: true,
			hourMin: 9,
			hourMax: 19,
			hourGrid: 1,
			showMinute: true,
			minuteGrid: 15,
			stepMinute: 15,

		};
		
		startDateTextBox.datetimepicker(datePickerStartPrefs);

		endDateTextBox.datetimepicker(datePickerEndPrefs);
		
		startBreakTextBox.datetimepicker(datePickerBreakPrefs);

		endBreakTextBox.datetimepicker(datePickerBreakPrefs);

	});  

    $(document).ready(function() {
        $('#id_also_include').attr('size', "10");
        $('#id_also_include').parent().css('display', 'inline-block');

        $('#id_dont_include').attr('size', "10");
        $('#id_dont_include').parent().css('display', 'inline-block');

        $('#submit-button').css('display', 'block');

    });