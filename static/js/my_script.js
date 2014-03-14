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

  $('.hovercard').hover(function() {
      $(this).stop(true, false).show();
  }, function() {
      $('.hovercard').hide();
  });
  $('.tracker-int').hover(function() {
      $(this).find('.hovercard').show(); // show() doesn't seem to work with delay
  }, function() {
      $(this).find('.hovercard').hide();
  });
});


