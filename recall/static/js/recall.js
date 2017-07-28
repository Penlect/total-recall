
/* ---------- KEYBOARD ---------- */

function RecallGrid(rows, columns, cell) {
	this.rows = rows;
	this.columns = columns;
	this.size = rows*columns;
	this.cell = cell;
	
	this.navigate = function(step){
	   var current_id = parseInt(this.cell.attr('id').split('_')[2]);
	   current_id = current_id + step;
	   if(current_id < 0 || current_id >= this.size){
			return this.cell;
	   }
	   else{
			return $('#recall_cell_' + current_id.toString());
	   }
	}
	
	this.select_next = function(){
		this.navigate(1).select();
	}
	
	this.select_previous = function(){
		this.navigate(-1).select();
	}
	
	this.select_up = function(){
		this.navigate(-this.columns).select();
	}
	
	this.select_down = function(){
		this.navigate(this.columns).select();
	}
	
	this.shift_right_row = function(){
		/*F: Set the current cell empty and move all aftercomming cells
		on this row one step to the right */
	   var current_id = this.cell.attr('id');
	   var new_value = '';
	   var prev_value = null;
	   var start = parseInt(current_id.split('_')[2]);
	   for(var i = start; i < this.columns*Math.ceil(start/this.columns); i++){
			var cell_id = '#recall_cell_' + i.toString();
			prev_value = $(cell_id).val();
			$(cell_id).val(new_value);
			new_value = prev_value;
	   }
	}
	
	this.shift_left_row = function(){
		/*B: Delete the current cell empty and move all aftercomming cells
		on this row one step to the left */
	   var current_id = this.cell.attr('id');
	   var new_value = '';
	   var prev_value = null;
	   var start = parseInt(current_id.split('_')[2]);
	   for(var i = this.columns*Math.ceil(start/this.columns) - 1; i >= start; i--){
			var cell_id = '#recall_cell_' + i.toString();
			prev_value = $(cell_id).val();
			$(cell_id).val(new_value);
			new_value = prev_value;
	   }
	}
	
	this.shift_right_after = function(){
		/*P: Set the current cell empty and move all aftercomming cells one step
		to the right */
	   var current_id = this.cell.attr('id');
	   var new_value = '';
	   var prev_value = null;
	   for(var i = parseInt(current_id.split('_')[2]); i < this.size; i++){
			var cell_id = '#recall_cell_' + i.toString();
			prev_value = $(cell_id).val();
			$(cell_id).val(new_value);
			new_value = prev_value;
	   }
	}
	
	this.shift_left_after = function(){
		/*M: Delete the current cell and move all aftercomming cells one step
		to the left */
	   var current_id = this.cell.attr('id');
	   var new_value = '';
	   var prev_value = null;
	   for(var i = this.size - 1; i >= parseInt(current_id.split('_')[2]); i--){
			var cell_id = '#recall_cell_' + i.toString();
			prev_value = $(cell_id).val();
			$(cell_id).val(new_value);
			new_value = prev_value;
	   }
	}
	
	this.set = function(value){
		this.cell.val(value);
	}
}

function keydownHandler(event, grid){
	   
	switch(event.which) {
		case 48: // 0
		case 49:
		case 50:
		case 51:
		case 52:
		case 53:
		case 54:
		case 55:
		case 56:
		case 57: // 9
			console.log("NUMERIC KEY: " + event.which);
			var digit = event.which - 48;
			grid.set(digit);
			grid.select_next();
			break;
		case 39: // Right Arrow
			console.log("RIGHT ARROW KEY: " + event.which);
		    grid.select_next();
			break;
		case 37: // Left Arrow
			console.log("LEFT ARROW KEY: " + event.which);
		    grid.select_previous();
			break;
		case 38: // Up Arrow
			console.log("UP ARROW KEY: " + event.which);
			grid.select_up();
			break;
		case 40: // Down Arrow
			console.log("DOWN ARROW KEY: " + event.which);
			grid.select_down();
			break;
		case 70: // F character
			console.log("RIGHT SHIFT BEFORE KEY: " + event.which);
			grid.shift_right_row();
			break;
		case 66: // B character
			console.log("LEFT SHIFT BEFORE KEY: " + event.which);
			grid.shift_left_row();
			break;
		case 80: // P character
			console.log("RIGHT SHIFT AFTER KEY: " + event.which);
			grid.shift_right_after();
			break;
		case 77: // M character
			console.log("LEFT SHIFT AFTER KEY: " + event.which);
			grid.shift_left_after();
			break;
		case 8: // Backspace
			console.log("BACKSPACE KEY: " + event.which);
		    grid.set('');
		    grid.select_previous();
		    break;
		case 46: // Del key
			console.log("DELETE KEY: " + event.which);
		    grid.set('');
		    grid.select_next();
		    break;
		default:
			console.log("INVALID KEY: " + event.which);
	}
}

function keydownHandlerWords(event, grid){
	switch(event.which) {
		case 49: // 1 (B) character
			console.log("LEFT SHIFT BEFORE KEY: " + event.which);
			event.preventDefault();
			grid.shift_left_row();
			break;
		case 50: // 2 (F) character
			console.log("RIGHT SHIFT BEFORE KEY: " + event.which);
			event.preventDefault();
			grid.shift_right_row();
			break;
		case 56: // 8 (M) character
			console.log("LEFT SHIFT AFTER KEY: " + event.which);
			event.preventDefault();
			grid.shift_left_after();
			break;
		case 57: // 9 (P) character
			console.log("RIGHT SHIFT AFTER KEY: " + event.which);
			event.preventDefault();
			grid.shift_right_after();
			break;
		case 39: // Right Arrow
			console.log("RIGHT ARROW KEY: " + event.which);
			event.preventDefault();
		    grid.select_down(); // For words
			break;
		case 37: // Left Arrow
			console.log("LEFT ARROW KEY: " + event.which);
			event.preventDefault();
		    grid.select_up(); // For words
			break;
		case 38: // Up Arrow
			console.log("UP ARROW KEY: " + event.which);
			event.preventDefault();
			grid.select_previous();
			break;
		case 13:
            // NO BREAK
		case 40: // Down Arrow
			console.log("DOWN ARROW KEY: " + event.which);
			event.preventDefault();
			grid.select_next();
			break;
		default:
			console.log("INVALID KEY: " + event.which);
	}
}

function keydownHandlerDates(event, grid){
	switch(event.which) {
		case 37: // Left Arrow
		case 38: // Up Arrow
			console.log("UP ARROW KEY: " + event.which);
			event.preventDefault();
			grid.select_previous();
			break;
		case 13:
		case 39: // Right Arrow
		case 40: // Down Arrow
			console.log("DOWN ARROW KEY: " + event.which);
			event.preventDefault();
			grid.select_next();
			break;
		default:
			console.log("INVALID KEY: " + event.which);
	}
}

/* ---------- TIMING ---------- */

var SECOND = 1000 // milliseconds

function getRecallTimer(sec_remaining_element, submit_element){
	var secondsRemaining = Number(sec_remaining_element.text());
	var interval = SECOND; // ms
	var expected = Date.now() + interval;
	function step() {
		secondsRemaining--;
		sec_remaining_element.text(secondsRemaining);
		if(secondsRemaining <= 0){
			console.log('Recall timeout -> Submit');
			submit_element.submit();
		}
		else{
			var dt = Date.now() - expected; // the drift (positive for overshooting)
			if (dt > interval) {
				console.log('Warning: dt = ' + dt);
			}
			expected += interval;
			recallTimer = setTimeout(step, Math.max(0, interval - dt)); // take into account drift
		}
	}
	return step;
}

/* ---------- CORRECTION ---------- */
function recallResultColor(recall_cell_id, result){
    if(result == 'correct'){
        $('#' + recall_cell_id).css('background-color', 'lime');
    }
    else if(result == 'wrong'){
        $('#' + recall_cell_id).css('background-color', '#ff0022');
    }
    else if(result == 'gap'){
        $('#' + recall_cell_id).css('background-color', '#ff0022');
    }
    else if(result == 'not_reached'){
        $('#' + recall_cell_id).css('background-color', '#eaeaea');
    }
    else if(result == 'off_limits'){
        $('#' + recall_cell_id).css('background-color', 'lightgray');
    }
    else if(result == 'almost_correct'){
        $('#' + recall_cell_id).css('background-color', '#ffff66');
    }
    else{
        console.log('Got unexpected result status: ' + result);
    }
}
