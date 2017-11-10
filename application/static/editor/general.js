$(document).ready(function() {
  var is_changed = 0;
  var editor = CodeMirror.fromTextArea
    (document.getElementById("code"), {
       extraKeys: {"Alt-F": "findPersistent"},
       extraKeys: {"Ctrl-F": "findPersistent"},
       lineNumbers: false,
       lineWrapping: true}
    );
    
  function save() {
    is_changed = 0;
    var height = document.getElementById("html_view").scrollTop;
    document.getElementById("html_scroll").value = height;
    var info = editor.getScrollInfo();
    document.getElementById("edit_scroll").value = info.top;
    editor.refresh();
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
  
  editor.on("change", function(){ changed_editor(); }  );
  editor.on("viewportChange", function(instance, from, to){ viewport_change_editor(instance, from, to); }  );
  
  //

  var charWidth = editor.defaultCharWidth(), basePadding = 3;
  editor.on("renderLine", function(cm, line, elt) {
    var off = CodeMirror.countColumn(line.text, null, cm.getOption("tabSize")) * charWidth;
    elt.style.textIndent = "-" + off + "px";
    elt.style.paddingLeft = (basePadding + off) + "px";
  });
  editor.refresh();
  
});