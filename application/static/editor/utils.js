// requer Jquery

$(document).ready(function () {
  function popitup(url) {
    newwindow = window.open(url,'name',',width=900');
    if (window.focus) {newwindow.focus()}
    return false;
  }
});