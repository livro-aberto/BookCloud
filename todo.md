# Urgent:

  - implement "steal branch" from parent owner
  - make security improvements on sphinx:
    - disallow raw html
    - read the documentation for more
      http://docutils.sourceforge.net/docs/ref/rst/directives.html#raw-data-pass-through

# Features:

  (priority)
  - commit text below commit message view
  - upload figures
    - use safe_join to avoid malicious filenames
    - size of figures (thumbnail for html, hd for pdf...)
  - more object types: discussion, issue, room,...
  - column for access rights? private (only owner), moderators of project, logged, public...
  - column for arbitrary data: json structure that is specific of the object type

  - remove title from comments (or let it be optional)

  (medium)
  - radio button with commit author in commit view (add external authors to database?)
  - ability to rename file (using git mv) (possibly with template for name)
  - ability to remove file
  - add template names for new files
  - implement delete project

  - implement other file types (besides rst). For this:
    - implement jinja for view<extension>.html
    - implement jinja for edit<extension>.html
    - add all the files (output of ls) in the branch view
    - replace build (for html and pdf) with a single makefile
      that once something has changed runs through all the
      file extensions and generate html, pdf and epub.

# Bugs:

  - bug in diff? see also https://github.com/lqc/google-diff-match-patch
  - add logging: http://damyanon.net/flask-series-logging/

# Interface:

  (important)
  - make all the links translatable (such as commit, requests...) and translate to Portuguese.
  - add branch visualizations including:
    modifications, diff with master, owner, subtree, requests, latest commits...

  (useful)
  - allow user to delete branch
  - ability to view old commits and branch from it. Now can only be done in GitHub.
  - add user options, such as: language
  - add project options  (see sphinx's conf.py)
    - such as: url, language, title...
    - add project_properties to be passed to jinja files, including for instance copyright
    - fix conf path in sphinx (pointing to /home/gutosurrex...)
  - to build an sql query in javascript, it may be useful to use:
    - a ready solution: http://querybuilder.js.org/
    - a recursive json schema:
      - http://jeremydorn.com/json-editor/
        ```
        { "$schema": "http://json-schema.org/draft-04/schema#",
          "definitions": {
            "batch": {
              "type": "object",
              "properties": {
                "content": {
                  "anyOf": [
                     { "type": "string" },
                     { "$ref": "#/definitions/batch" }
                  ]
                }
              }
            }
          },
          "type": "object",
          "properties": {
            "billing_address": { "$ref": "#/definitions/batch" },
            "shipping_address": { "$ref": "#/definitions/batch" }
          }
        }
        ```

# Organization of code:

  - increase base test to include: commenting
  - organize view.py into different files: git functions...
  - put helper functions to a separate file and import it in view.py
  - replace all possible function calls using names to objects (user, project, branch...)
  - create a function to fix file.extension handling
  - is it possible to remove all the menu = menu_bar() calls, by using context processors?
  - implement submodules for javascript code,
    - https://github.com/lqc/google-diff-match-patch
    - https://github.com/sphinx-doc/sphinx/tree/master/sphinx/themes/bizstyle/static
    - https://github.com/mathjax/MathJax
  - fix BookCloud.wsgi to use a configuration value as path

# Codemirror addons:

  - dialog for latex/image help: https://codemirror.net/doc/manual.html#addon_dialog
  - trailing whitespace: https://codemirror.net/demo/trailingspace.html
  - code folding: https://codemirror.net/demo/folding.html
  - marks and comments on text: https://codemirror.net/demo/lint.html
  - mark the line where the cursor is: https://codemirror.net/demo/activeline.html
  - full screen: https://codemirror.net/demo/fullscreen.html

# Sphinx extensions

A big list is found in:
https://sphinxext-survey.readthedocs.io/en/latest/

  - gnuplot: produces images using gnuplot_ language
  - issuetracker: link to different issue trackers
  - A generic “todo like” nodes: https://pypi.python.org/pypi/sphinxcontrib-gen_node
  - tags: https://github.com/spinus/sphinxcontrib-taglist
  - sphinxcontrib-fulltoc
    Include a full table of contents in your sidebarhttps:
    https://sphinxcontrib-fulltoc.readthedocs.io/en/latest/

