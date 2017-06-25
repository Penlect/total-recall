$(document).ready(function(){

   var currCell = $('td').first();
   var editing = false;

   // User clicks on a cell
   $('td').click(function() {
       currCell = $(this);
       edit();
   });

   // Show edit box
   function edit() {
       editing = true;
       currCell.toggleClass("editing");
       $('#edit').show();
       $('#edit #text').val(currCell.html());
       $('#edit #text').select();
   }

   // User saves edits
   $('#edit form').submit(function(e) {
       editing = false;
       e.preventDefault();
       // Ajax to update value in database
       $.get('#', '', function() {
           $('#edit').hide();
           currCell.toggleClass("editing");
           currCell.html($('#edit #text').val());
           currCell.focus();
       });
   });

   // User navigates table using keyboard
   $('table').keydown(function (e) {
       var c = "";
       if (e.which == 39) {
           // Right Arrow
           c = currCell.next();
       } else if (e.which == 37) { 
           // Left Arrow
           c = currCell.prev();
       } else if (e.which == 38) { 
           // Up Arrow
           c = currCell.closest('tr').prev().find('td:eq(' + 
             currCell.index() + ')');
       } else if (e.which == 40) { 
           // Down Arrow
           c = currCell.closest('tr').next().find('td:eq(' + 
             currCell.index() + ')');
       } else if (e.which == 13) { 
           // Enter
           e.preventDefault();
           c = currCell.closest('tr').next().find('td:eq(' + 
             currCell.index() + ')');
       } else if (!editing && (e.which == 13 || e.which == 32)) { 
           // Enter or Spacebar - edit cell
           e.preventDefault();
           edit();
       } else if (!editing && (e.which == 9 && !e.shiftKey)) { 
           // Tab
           e.preventDefault();
           c = currCell.next();
       } else if (!editing && (e.which == 9 && e.shiftKey)) { 
           // Shift + Tab
           e.preventDefault();
           c = currCell.prev();
       } 

       // If we didn't hit a boundary, update the current cell
       if (c.length > 0) {
           currCell = c;
           currCell.focus();
       }
   });

   // User can cancel edit by pressing escape
   $('#edit').keydown(function (e) {
       if (editing && e.which == 27) { 
           editing = false;
           $('#edit').hide();
           currCell.toggleClass("editing");
           currCell.focus();
       }
   });
});