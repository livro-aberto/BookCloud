$(document).ready(function() {
  sphinx_apply_uikit();
  var is_changed = 0;
  
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
        UIkit.notification('Saved!', {status: 'success', pos: 'bottom-center'});
        $.get(form.attr('action'), function(data) {
          var retorno = $(data).find(".documentwrapper");
          $(".document").html('');
          $(".document").html(retorno);
          sphinx_apply_uikit();
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
  $(".insert-around").click(function() {
    insertAround(editor, $(this).attr('data-insert-start'), $(this).attr('data-insert-end'));
  });
  
  $("#menu_insert_style > li > a").click(function(e) {
    insertAround(editor, $(this).attr('data-insert-start'), $(this).attr('data-insert-end'));
  });
  
  $("#menu_insert_sections > li > button").add(".insert-sec-button").click(function(e) {
    $('.uk-dropdown').hide();
    UIkit.modal($("#sections_modal")).show();
    $("#sections_modal").attr('data-type', $(this).attr('data-type'));
  });
  
  $(".insert-box-button").click(function(e) {
    $('.uk-dropdown').hide();
    UIkit.modal($("#boxes_modal")).show();
    $("#boxes_modal").attr('data-title', $(this).attr('data-title'));
  });
  
  $("#insert_section_button").click(function() {
    insertSections($("#sections_modal").attr('data-type'), $("#insert_section_title").val());
    UIkit.modal($("#sections_modal")).hide()
  });
  
  $("#insert_box_button").click(function() {
    insertBoxes($("#boxes_modal").attr('data-title'), $("#insert_box_text").val());
    UIkit.modal($("#boxes_modal")).hide()
  });
  
  $('.insert-image-button').click(function() {
    UIkit.modal($("#insert_image_modal")).show();
  });
  
  $(".popitup").click(function() {
    popitup($(this).attr('data-url'));
  });
  
});