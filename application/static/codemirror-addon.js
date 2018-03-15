$(document).ready(function(){

  var is_changed = 0;
  // inserts text around the cursor or selection
  function insertAround(start, end) {
    var doc = editor;
    var cursor = doc.getCursor();
    if (doc.somethingSelected()) {
      var selection = doc.getSelection();
      doc.replaceSelection(start + selection + end);
    } else {
      // If no selection then insert start and end args and set cursor position between the two.
      doc.replaceRange(start + end, { line: cursor.line, ch: cursor.ch });
      doc.setCursor({ line: cursor.line, ch: cursor.ch + start.length });
    }
    editor.focus();
  }

  var colorLookUp = [
    "", "red-background", "red-background",
    "green-background", "red-background", "red-background",
    "yellow-background", "red-background", "red-background",
    "blue-background", "red-background", "red-background",
    "", "red-background", "red-background",
    "green-background", "red-background", "red-background",
    "yellow-background", "red-background", "red-background",
    "blue-background", "red-background", "red-background",
    "", "red-background", "red-background",
    "green-background", "red-background", "red-background",
    "yellow-background", "red-background", "red-background",
    "blue-background", "red-background", "red-background"
  ];

  var lineNumber;
  var numberWhiteSpaces;

  /*editor.eachLine(function(lineNumber) {
    numberWhiteSpaces = editor.getLine(lineNumber).search(/\S|$/);
    editor.addLineClass(lineNumber, "background", colorLookUp[numberWhiteSpaces]);
  });
  */

  function getLines() {
    var count = editor.lineCount(), i;
    for (i = 0; i < count; i++) {
      numberWhiteSpaces = editor.getLine(i).search(/\S|$/);
      editor.addLineClass(i, "background", colorLookUp[numberWhiteSpaces]);
    }
  }
  getLines();

  editor.on("change", function() {
    //console.log("A");
    lineNumber = editor.getCursor()["line"];
    numberWhiteSpaces = editor.getLine(lineNumber).search(/\S|$/);
    //console.log(lineNumber);
    console.log(numberWhiteSpaces);
    console.log(colorLookUp[numberWhiteSpaces]);
    //if ((numberWhiteSpaces % 3) != 0) {
    //  console.log("A");
    editor.removeLineClass(lineNumber, "background", "red-background");
    editor.removeLineClass(lineNumber, "background", "green-background");
    editor.removeLineClass(lineNumber, "background", "yellow-background");
    editor.removeLineClass(lineNumber, "background", "blue-background");
    editor.addLineClass(lineNumber, "background", colorLookUp[numberWhiteSpaces]);
    //} else {
    //}
  });
});
