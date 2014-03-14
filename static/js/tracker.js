$(document).ready(function() {
  /*
  ################################################
  Hovercard
  ################################################
  */
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


  /*
  ################################################
  Lazy Search Jquery
  ################################################
  */

  $("#interviewerSearchInput").keyup(function () {

      // NEW selector
      jQuery.expr[':'].Contains = function(a, i, m) {
        return jQuery(a).text().toUpperCase()
            .indexOf(m[3].toUpperCase()) >= 0;
      };

      // OVERWRITES old selecor
      jQuery.expr[':'].contains = function(a, i, m) {
        return jQuery(a).text().toUpperCase()
            .indexOf(m[3].toUpperCase()) >= 0;
      };

      //split the current value of searchInput
      var data = this.value.split(" ");
      //create a jquery object of the rows
      var jo = $(".tracker-container").find("tr");
      var tracker_group = $(".tracker-interview-group") 
      if (this.value == "") {
          jo.show();
          tracker_group.show()
          return;
      }
      //hide all the rows
      jo.hide();
      tracker_group.hide()

      //Recusively filter the jquery object to get results.
      jo.filter(function (i, v) {
          var $t = $(this);
          for (var d = 0; d < data.length; ++d) {
              if ($t.is(":contains('" + data[d] + "')")) {
                  $t.parent().parent().parent().find('.tracker-interview-group').show()
                  return true;
              }
          }
          return false;
      })
      //show the rows that match.
      .show();
  }).focus(function () {
      this.value = "";
      $(this).css({
          "color": "black"
      });
      $(this).unbind('focus');
  }).css({
      "color": "#C0C0C0"
  });

  $('#groupSearchInput').keyup(function(){
     var valThis = $(this).val().toLowerCase();
      $('#tracker-ul>li').each(function(){
       var text = $(this).text().toLowerCase();
          (text.indexOf(valThis) == 0) ? $(this).show() : $(this).hide();            
     });
  });

  /*
  ################################################
  Color Jquery
  ################################################
  */

  var red = new Hex(0xFFD4C9).range(new Hex(0xFF3B30), 7, true);
  var orange = new Hex(0xFFFF99).range(new Hex(0xFF9500), 7, true);
  var green = new Hex(0xE5FFFD).range(new Hex(0x4CD964), 7, true);
  var blue = new Hex(0x99FFFF).range(new Hex(0x007AFF), 7, true);
  var purple = new Hex(0xF1EFFF).range(new Hex(0x5856D6), 7, true);
  var pink = new Hex(0xFFC6EE).range(new Hex(0xFF2D55), 7, true);
  var grey = new Hex(0xEAEAEF).range(new Hex(0x8E8E93), 7, true);
  var magenta = new Hex(0xFFE6FF).range(new Hex(0xEF4DB6), 7, true);

  var color_gradient = {
      'red': red,
      'orange': orange,
      'green': green,
      'blue': blue,
      'purple': purple,
      'pink': pink,
      'grey': grey,
      'magenta': magenta
  };

  function IsNumeric(input)
  {
      return (input - 0) == input && (''+input).replace(/^\s+|\s+$/g, "").length > 0;
  }

  $("table tr td").each(function (){
      var chosen_color = color_gradient[$(this).parent().parent().parent().attr('color_group')];
      var opacity = 1;
      if (IsNumeric($(this).attr('value')) == true){
          opacity = parseInt($(this).attr('value')) + 1;
      }
      $(this).css({
      'background-color' : '#'+chosen_color[opacity].toString()
      });
  });

});

