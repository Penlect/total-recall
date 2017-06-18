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
	
	this.shift_left = function(){
	   var current_id = this.cell.attr('id');
	   var new_value = '';
	   var prev_value = null;
	   for(var i = parseInt(current_id.split('_')[2]); i >= 0; i--){
			var cell_id = '#recall_cell_' + i.toString();
			prev_value = $(cell_id).val();
			$(cell_id).val(new_value);
			new_value = prev_value;
	   }
	}
	
	this.shift_right = function(){
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
		case 80: // P character
			console.log("RIGHT SHIFT KEY: " + event.which);
			grid.shift_right()
			break;
		case 77: // M character
			console.log("LEFT SHIFT KEY: " + event.which);
			grid.shift_left()
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