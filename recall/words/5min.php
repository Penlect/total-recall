<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"> 
<link href="bootstrap/css/bootstrap.min.css" rel="stylesheet" media="screen">
<script src="http://ajax.googleapis.com/ajax/libs/jquery/1.11.1/jquery.min.js"></script>
<script src="bootstrap/js/bootstrap.min.js"></script>
<style>
table, td, tr{
border:1px solid black;
border-collapse: collapse;
table-layout: fixed;
}
table{
width:900px;
}
.row_column{
width:100px;
}
body{
margin-left:20px;
margin-bottom:20px;
}
td{
padding-left:3px;
}
</style>
</head>

<?php
//$fid = fopen('swe.txt', 'r') or die('Unable to open file!');
$lines = file('swe.txt', FILE_IGNORE_NEW_LINES);
shuffle($lines);
//var_dump($lines);
$nrRows = 6;
$nrWordsInColumn = 20;
$nrWords = $nrWordsInColumn * $nrRows;
$lines = array_slice($lines, 0, $nrWords);
$memotime = 300;
$recalltime = 900;
$coutdownstep = 5;
?>

<body>

<div id='recallsheet' style='display: none;'>
<h1 id='recallheader'>5 Min Words - Recall</h1>
<p id="timerrecall"><?php echo $recalltime; ?> secs</p>
<table>
<tr>
<?php
for ($x = 0; $x < $nrWordsInColumn; $x++) {
   echo "<td class='row_column'><strong>Row " . ($x+1) . "</strong></td>";
   for ($y = $x; $y < $nrWords; $y = $y + $nrWordsInColumn) {
      echo "<td id='" . $y . "' tabindex=" . $y . " contenteditable='true'></td>";
   }
   echo "</tr><tr>";
}
?>
</tr>
</table>
<p style='margin-top:10px;'>
<button id='finish' class='btn btn-primary'>Finish</button>
</p>
</div>

<div id='memosheet'>
<h1>5 Min Words - Memorization</h1>
<p id="timermemo"><?php echo $memotime; ?> secs</p>
<table>
<tr>
<?php
for ($x = 0; $x < $nrWordsInColumn; $x++) {
   echo "<td class='row_column'><strong>Row " . ($x+1) . "</strong></td>";
   for ($y = $x; $y < $nrWords; $y = $y + $nrWordsInColumn) {
      echo "<td>" . $lines[$y] . "</td>";
   }
   echo "</tr><tr>";
}
?>
</tr>
</table>
</div>

<script>

function isEmpty(str) {
    return (!str || 0 === str.length);
}

function startTimer(element, sec){
   var count = sec;
   var counter=setInterval(timer, <?php echo ($coutdownstep*1000); ?>); //1000 will  run it every 1 second
   function timer()
   {
     count = count - <?php echo $coutdownstep; ?>;
     if (count <= 0)
     {
        clearInterval(counter);
        return;
     }
     document.getElementById(element).innerHTML=count + " secs";
   }
}

var data = <?php echo json_encode($lines);?>;

$(document).ready(function(){

   startTimer("timermemo", <?php echo ($memotime); ?>);

   setTimeout(function(){
   
      $("#memosheet").hide();
      
      $('#recallsheet').show(function(){
         startTimer("timerrecall", <?php echo ($recalltime); ?>);
         setTimeout(function(){
            finish();
         },<?php echo ($recalltime*1000); ?>);
         
      });
      
   },<?php echo ($memotime*1000); ?>);
   
   
   
   function finish(){
      $('p').hide();
      $('#finish').hide();
      $('td').removeAttr('contenteditable');
      for (i = 0; i < <?php echo $nrWords; ?>; i++){
         if (isEmpty($('#'+i).text())){
            $('#'+i).css("background-color","#E8E8E8  ");
         }
         else{
            if ($('#'+i).text() == data[i]){
               $('#'+i).css("background-color","#00FF00");
            }
            else{
               $('#'+i).css("background-color","#FF0000");
            }
         }
      }
      $('#memosheet').show();
      $('#recallheader').text('5 Min Words - Result');
   }
   
   $('#finish').click(function(){
      finish();
   });
   
});
</script>

<script src='navigation.js'></script>

</body>
</html>