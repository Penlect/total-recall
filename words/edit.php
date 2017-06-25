<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"> 
<link href="bootstrap/css/bootstrap.min.css" rel="stylesheet" media="screen">
<script src="http://ajax.googleapis.com/ajax/libs/jquery/1.11.1/jquery.min.js"></script>
<script src="bootstrap/js/bootstrap.min.js"></script>
<style>
table, td, tr{
//border: 1px solid black;
border-collapse: collapse;
table-layout: fixed;
}
table{
width:250px;
}
body{
margin-left:20px;
margin-bottom:20px;
}
td{
padding-left:3px;
}
.word{
cursor: pointer;
cursor: hand;
}
.lineCol{
width:55px;
}
.deleted{
color:red;
font-weight:bold;
}
</style>

<script>
$(document).ready(function(){
   var wordlist = {};
  $(".word").click(function(){
    $(this).toggleClass('deleted');
    if(!(this.id in wordlist)){
      wordlist[this.id] = $(this).text();
      $('#to_be_deleted tr:last').after('<tr id=' + this.id + '_to_delete><td class="lineCol">' + this.id + '</td><td>' + $(this).text() + '</td></tr>');
    }
    else{
      delete wordlist[this.id];
      $('#' + this.id + '_to_delete').remove();
    }
    if(true){
      $('#submit_button').show();
    }
    else{
      $('#submit_button').hide();
    }
    var jsonString = JSON.stringify(wordlist);
    $('#to_delete').val(jsonString);
  });
});
</script>

</head>

<?php
//$fid = fopen('swe.txt', 'r') or die('Unable to open file!');
$words = file('swe.txt', FILE_IGNORE_NEW_LINES);
//var_dump($words);
$deleted = file('deleted.txt', FILE_IGNORE_NEW_LINES);

if( isset($_POST['delete_this']) )
{
     $data = json_decode($_POST['delete_this'], true);
     
     $deleted = file('deleted.txt', FILE_IGNORE_NEW_LINES);
     foreach($data as $word){
         array_push($deleted, $word);
     }
     sort($deleted);
     file_put_contents('deleted.txt', implode(PHP_EOL, $deleted));
     
     $words = array_diff($words, $data);
     file_put_contents('swe.txt', implode(PHP_EOL, $words));
     $words = array_values($words);
}

?>

<body>


<div class='container'>

<div class='row'>

<div class='col-md-4'>

<h1>Current Words</h1>

<table>
<?php
for ($x = 0; $x < count($words); $x++) {
   echo "<tr><td class='lineCol'>" . $x . "</td><td id='" . $x . "' class='word'>" . $words[$x] . "</td></tr>";
}
?>
</table>
</div>

<div class='col-md-4'>
<h1>To be deleted</h1>
<table id='to_be_deleted'>
<tr><td class="lineCol"></td><td></tr>
</table>

<p>
<form role='form' action='edit.php' method='POST'>
<button id='submit_button' style='display:none;' type='submit' class='btn btn-primary'>Submit changes</button>
<input id='to_delete' style='display:none;' type='text' name='delete_this' value='fdfdf'/>
</form>
</p>

<div id='temp'></div>

</div>


<div class='col-md-4'>

<h1>Have been deleted</h1>

<table>
<?php
for ($x = 0; $x < count($deleted); $x++) {
   echo "<tr><td class='lineCol'>" . $x . "</td><td>" . $deleted[$x] . "</td></tr>";
}
?>
</table>

</div>

</div>
</div>

</body>
</html>