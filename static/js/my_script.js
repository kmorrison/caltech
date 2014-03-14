$(document).ready(function() {
  $( "#date-picker" ).datepicker();

  $("#scheduler_form").submit(function(event){
        $.ajax({
             type:"POST",
             url:"/new_scheduler_post/",
             data: $("#scheduler_form").serialize(),
             success: function(){
                 $('#result').html("<p>Success!</p>") 
             }
        });
        return false;
  });
});


