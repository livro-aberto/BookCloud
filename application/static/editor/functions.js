function makeIndicators(char, times) {
    return Array(times+1).join(char);
}

function slugify(string) {
  return slug(string.toLowerCase())
}
  
function insertAround(editor, start, end) {
  var doc = editor;
  var linha = get_word(doc);
  var cursor = doc.getCursor();
  
  if (!end) {
    end = ""
  } 
  
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

function insertLink(text, url) {
    var linha = " `"+text+" <"+url+">`_ ";
    insertAround(editor, "", linha);
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
  
  var data = "";
  
  if (type == "cap") {
    var directive = "\n\n.. "+item_id+":\n\n";
    var delimiter = makeIndicators("*", item_title.length);
    delimiter = delimiter+'\n';
    data = directive+delimiter+item_title+"\n"+delimiter+"\n";
  }
  
  if (type == "sec") {
    var directive = "\n\n.. "+CURRENT_SEC+"-"+item_id+":\n\n";
    var delimiter = makeIndicators("=", item_title.length);
    delimiter = '\n'+delimiter+'\n';
    data = directive+item_title+delimiter+"\n";
  }
  
  if (type == "sub") {
    var directive = "\n\n.. "+item_id+":\n\n";
    var delimiter = makeIndicators('-', item_title.length);
    delimiter = '\n'+delimiter+'\n';
    data = directive+item_title+delimiter+"\n";
  }
  
  if (type == "ativ") {
    var directive = "\n\n.. "+item_id+":\n\n";
    var delimiter = '\n'+makeIndicators('-', item_title.length)+'\n';
    data = directive+"\nAtividade: "+item_title+delimiter+'\n';
  }
  
  editor.replaceRange(data, {line: cursor.line});
  
}

function splitIntoLines(text) {
    var formatted = "";
    text.split("\n").forEach(function(item, index) {
        formatted += "   "+item+"\n";
      });
    return formatted;
}

function insertAmbiente(data) {
  var cursor = editor.getCursor();
  var item_id = slugify(data.title);
  var sec_id = data.section;
  
  editor.setCursor({line: cursor.line});
  
  var my_id = "ativ-"+sec_id+"-"+item_id;
  var text = ".. "+my_id+":\n\nAtividade: "+data.title;
  text = text+"\n"+makeIndicators('-', data.title.length+11)+"\n\n";
  text = text+".. admonition:: Para o professor\n\n";
  text += "    **Objetivos específicos:**\n";
  text += splitIntoLines(data.objetivos);
  text += "\n\n    **Recomendações e sugestões:**\n";
  text += splitIntoLines(data.recomendacoes) + "\n\n";
  text += data.texto;
  text += "\n\n.. admonition:: Resposta\n\n";
  text += splitIntoLines(data.resposta)+"\n\n";
  
  editor.replaceRange(text, {line: cursor.line});
}

function insertBoxes(title, text) {
  var cursor = editor.getCursor();
  editor.setCursor({line: cursor.line});
  
  var splitted = text.split("\n")
  
  var val = '\n\n.. admonition:: '+title+' \n\n';
  
  editor.replaceRange(val, {line: cursor.line});
  
  splitted.forEach(function(item, index) {
      cursor = editor.getCursor();
      editor.replaceRange("   "+item+"\n", {line: cursor.line});
      editor.setCursor({line: cursor.line+1});
  });
}

function save() {
  var height = document.getElementById("html_view").scrollTop;
  document.getElementById("html_scroll").value = height;
  var info = editor.getScrollInfo();
  document.getElementById("edit_scroll").value = info.top;
}
  
function popitup(url) {
  newwindow = window.open(url,'name',',width=900');
  if (window.focus) {newwindow.focus()}
  return false;
}

function get_word(editor, line=null, inicio=null, fim=null, ch=null) {
  var cursor = editor.getCursor();
  if (line == null) {
    line = cursor.line;
  }
  
  if (ch == null) {
    var ch = cursor.ch;
  }
  
  if (inicio == null) {
    inicio = editor.findWordAt({line: line, ch: ch}).anchor.ch;
  }
  
  if (fim == null) {
    fim = editor.findWordAt({line: line, ch: ch}).head.ch;
  }

  var l = editor.getRange({line: line, ch: inicio}, {line: line, ch: fim});
  
  return {'word': l, 'inicio': inicio, 'fim': fim, 'linha': line}
}