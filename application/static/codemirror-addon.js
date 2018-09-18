function getLevel(editor, lineNumber) {
  let line = editor.getLine(lineNumber);
  let indication = line.search(/\S|$/);
  if ((line.length >= indication + 3)
      && (line.substring(indication, indication + 3) === ".. ")) {
    indication = indication + 3;
  }
  if (lineNumber === 0) {
    return indication;
  }
  if(line === "") {
    line = editor.getLine(lineNumber - 1);
    indication = line.search(/\S|$/);
    if ((line.length >= indication + 3)
        && (line.substring(indication, indication + 3) === ".. ")) {
      indication = indication + 3;
    }
    return indication;
  }
  return indication;
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

function getLines() {
  var doc = editor
  var count = editor.lineCount(), i;
  for (i = 0; i < count; i++) {
    numberWhiteSpaces = getLevel(editor, i);
    editor.addLineClass(i, "background", colorLookUp[numberWhiteSpaces]);
  }
}


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
  getLines();
}


$(document).ready(function(){

  var is_changed = 0;
  // inserts text around the cursor or selection

  var lineNumber;
  var numberWhiteSpaces;

  /*editor.eachLine(function(lineNumber) {
    numberWhiteSpaces = editor.getLine(lineNumber).search(/\S|$/);
    editor.addLineClass(lineNumber, "background", colorLookUp[numberWhiteSpaces]);
  });
  */

  function clearClass(editor, lineNumber) {
    editor.removeLineClass(lineNumber, "background", "red-background");
    editor.removeLineClass(lineNumber, "background", "green-background");
    editor.removeLineClass(lineNumber, "background", "yellow-background");
    editor.removeLineClass(lineNumber, "background", "blue-background");
  }

  getLines();

  editor.on("change", function() {
    //console.log("A");
    lineNumber = editor.getCursor()["line"];
    numberWhiteSpaces = getLevel(editor, lineNumber);
    //console.log(lineNumber);
    //console.log(numberWhiteSpaces);
    //console.log(colorLookUp[numberWhiteSpaces]);
    //if ((numberWhiteSpaces % 3) != 0) {
    //  console.log("A");
    clearClass(editor, lineNumber);
    editor.addLineClass(lineNumber, "background", colorLookUp[numberWhiteSpaces]);
    //} else {
    //}
  });

  editor.on("beforeChange", function(cm, obj) {
    var text = obj['text'];
    var new_text = [text[0].replace(/[\u0250-\ue007]/g, ' INVALID CHARACTER ')];
    if (/[\u0250-\ue007]/g.test(text[0])) {
      obj.update(obj['from'], obj['to'], new_text);
    }
  });
});
