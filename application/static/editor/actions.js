// requer Jquery

$(document).ready(function () {
  function insertAround(editor, start, end) {
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
  
  function save() {
    is_changed = 0;
    var height = document.getElementById("html_view").scrollTop;
    document.getElementById("html_scroll").value = height;
    var info = editor.getScrollInfo();
    document.getElementById("edit_scroll").value = info.top;
    editor.refresh();
  }
});