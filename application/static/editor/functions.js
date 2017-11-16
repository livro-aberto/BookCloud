function slugify(string) {
  return slug(string.toLowerCase())
}
  
function insertAround(editor, start, end) {
  var doc = editor;
  var linha = get_word(doc)
  var cursor = doc.getCursor();
  if (doc.somethingSelected()) {
    var selection = doc.getSelection();
    doc.replaceSelection(start + selection + end);
  } else {
    if (linha.word != "") {
      doc.replaceRange(start+linha.word+end, {line: linha.linha, ch: linha.inicio}, {line: linha.linha, ch: linha.fim});
      doc.setCursor({line: linha.linha, ch: linha.fim+start.length+end.length});
    } else {
      // If no selection then insert start and end args and set cursor position between the two.
      doc.replaceRange(start + end, { line: cursor.line, ch: cursor.ch });
      doc.setCursor({ line: cursor.line, ch: cursor.ch + start.length });
    }
  }
  editor.focus();
}

function insert_image(url, name, caption, width, align) {
  var str_slug = slug(name.toLowerCase());
  var data = '\n.. '+str_slug+':\n\n.. figure:: '+url+'\n   :width: '+width+'pt\n   :align: '+align+'\n\n   '+caption;
  
  editor.setCursor({line: cursor.line});
  editor.replaceRange(data, {line: cursor.line});
}

function insertSections(type, title) {
  var cursor = editor.getCursor();
  var item_title = title;
  var item_id = slugify(item_title);
  
  editor.setCursor({line: cursor.line});
  
  var data = ""
  
  if (type == "cap") {
    var directive = "\n\n.. "+item_id+":\n\n";
    var delimiter = "********\n"
    data = directive+delimiter+item_title+"\n"+delimiter+"\n"
  }
  
  if (type == "sec") {
    var directive = "\n\n.. "+item_id+":\n\n";
    var delimiter = "\n======\n"
    data = directive+item_title+delimiter+"\n"
  }
  
  if (type == "sub") {
    var directive = "\n\n.. "+item_id+":\n\n";
    var delimiter = "\n---------\n"
    data = directive+item_title+delimiter+"\n"
  }
  
  if (type == "ativ") {
    var directive = "\n\n.. "+item_id+":\n\n";
    var delimiter = "\n------------------------------\n";
    data = directive+"\nAtividade: "+item_title+delimiter+'\n'
  }
  
  editor.replaceRange(data, {line: cursor.line});
  
}

function insertBoxes(title, text) {
  var cursor = editor.getCursor();
  editor.setCursor({line: cursor.line});
  
  var val = '\n\n.. admonition:: '+title+' \n\n   '+text
  
  editor.replaceRange(val, {line: cursor.line});
}

function save() {
  is_changed = 0;
  var height = document.getElementById("html_view").scrollTop;
  document.getElementById("html_scroll").value = height;
  var info = editor.getScrollInfo();
  document.getElementById("edit_scroll").value = info.top;
  editor.refresh();
}
  
function popitup(url) {
  newwindow = window.open(url,'name',',width=900');
  if (window.focus) {newwindow.focus()}
  return false;
}

function get_word(editor) {
  var cursor = editor.getCursor();
  
  var line = cursor.line;
  var ch = cursor.ch;

  var inicio = editor.findWordAt({line: line, ch: ch}).anchor.ch;
  var fim = editor.findWordAt({line: line, ch: ch}).head.ch;

  var l = editor.getRange({line: line, ch: inicio}, {line: line, ch: fim});
  
  return {'word': l, 'inicio': inicio, 'fim': fim, 'linha': line}
}