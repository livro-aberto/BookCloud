$(document).ready(function() {
  var is_changed = 0;
  var editor = CodeMirror.fromTextArea
    (document.getElementById("code"), {
       extraKeys: {"Alt-F": "findPersistent"},
       extraKeys: {"Ctrl-F": "findPersistent"},
       lineNumbers: false,
       lineWrapping: true}
    );
    
  function slugify(string) {
    return string
      .toString()
      .trim()
      .toLowerCase()
      .replace(/\s+/g, "_")
      .replace(/[^\w\-]+/g, "-")
      .replace(/\-\-+/g, "-")
      .replace(/^-+/, "")
      .replace(/-+$/, "");
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
  
  function insertSections(type, title) {
    var cursor = editor.getCursor();
    var item_title = title;
    var item_id = slugify(item_title);
    
    editor.setCursor({line: cursor.line, ch: 0});
    
    var data = ""
    
    if (type == "cap") {
      var directive = "\n\n.. "+item_id+":\n";
      var delimiter = "********\n"
      data = directive+delimiter+item_title+"\n"+delimiter+"\n"
    }
    
    if (type == "sec") {
      var directive = "\n\n.. "+item_id+":\n";
      var delimiter = "\n======\n"
      data = directive+item_title+delimiter+"\n"
    }
    
    if (type == "sub") {
      var directive = "\n\n.. "+item_id+":\n";
      var delimiter = "\n---------\n"
      data = directive+item_title+delimiter+"\n"
    }
    
    editor.replaceRange(data, { line: cursor.line, ch: cursor.ch });
    
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
  
  $(window).bind('beforeunload', function(e){
    if (is_changed == 1) return true;
    else e=null;
  });
  
  $('#myform').submit(function(ev) {
    ev.preventDefault();
    var form = $('#myform');
    var jqxhr = $.post(form.attr('action'), form.serialize(), function(data) {
      
    })
      .done(function(data) {
        UIkit.notification('Salvo com sucesso!', {status: 'success', pos: 'bottom-center'});
        $.get(form.attr('action'), function(data) {
          var retorno = $(data).find(".documentwrapper");
          $(".document").html('');
          $(".document").html(retorno);
        });
      })
      .fail(function(data) {
        alert( "error" );
      })
      .always(function(data) {
        
      });
    save();
  });
  
  $('#preview').click(function(ev) {
    $('#myform').submit();
  });
  
  // Eventos
  function changed_editor(instance, changeObj) {
    is_changed = 1;
    editor.save();
  }
  
  function viewport_change_editor(instance, from, to) {
    
  }
  
  function cursor_activity(instance) {
    
    //console.log(get_word(editor));
  }
  editor.on("change", function(){ changed_editor(); }  );
  editor.on("viewportChange", function(instance, from, to){ viewport_change_editor(instance, from, to); }  );
  editor.on("cursorActivity", function(){ cursor_activity(); }  );
  //

  var charWidth = editor.defaultCharWidth(), basePadding = 3;
  editor.on("renderLine", function(cm, line, elt) {
    var off = CodeMirror.countColumn(line.text, null, cm.getOption("tabSize")) * charWidth;
    elt.style.textIndent = "-" + off + "px";
    elt.style.paddingLeft = (basePadding + off) + "px";
  });
  editor.refresh();
  
  
  // Edit Bar
  $("#menu_insert_style > li > a").click(function(e) {
    insertAround(editor, $(this).attr('data-insert-start'), $(this).attr('data-insert-end'));
  });
  
  $("#menu_insert_sections > li > button").click(function(e) {
    UIkit.modal($("#sections_modal")).show();
    $("#sections_modal").attr('data-type', $(this).attr('data-type'));
  });
  
  $("#insert_section_button").click(function() {
    insertSections($("#sections_modal").attr('data-type'), $("#insert_section_title").val());
    UIkit.modal($("#sections_modal")).hide()
  });
  
  $(".popitup").click(function() {
    popitup($(this).attr('data-url'));
  });
  
});