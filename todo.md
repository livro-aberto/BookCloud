# Urgent:

  - implement "steal branch" from parent owner
  - limit number of visits: https://flask-limiter.readthedocs.io/en/stable/
  - allow user to delete branch (setup expiration time for branches?)

# Features:

  (priority)
  - commit text below commit message
  - upload figures
    - use safe_join to avoid malicious filenames
  - implement comments and issues
    - I would use something like an integer id for the thread and then
      each comment has its thread and an id of the form:
      6d8db9:b8237d:c23d79:cd0079:a29822:233a13
      (6 digits for each sublevel: 16^6 = 16.7 x 10^6)
    - preserving order with hexadecimals:
      (a < b) == (format(a, '08X') < format(b, '08X'))

  (medium)
  - ability to rename file (possibly with template for name)
  - ability to remove file
  - add template names for new files
  - implement delete project

# Bugs:

  - bug in diff? see also https://github.com/lqc/google-diff-match-patch
  - add logging: http://damyanon.net/flask-series-logging/

# Interface:

  (important)
  - make all the links translatable (such as commit, requests...) and translate to Portuguese.
  - add branch visualizations including:
    modifications, diff with master, owner, subtree, requests, latest commits...

  (useful)
  - ability to view old commits and branch from it. Now can only be done in GitHub.
  - add user options, such as: language
  - add project options  (see sphinx's conf.py)
    - such as: url, language, title...
    - add project_properties to be passed to jinja files, including for instance copyright
    - fix conf path in sphinx (pointing to /home/gutosurrex...)

# Organization of code:

  - put helper functions to a separate file and import it in view.py
  - replace all possible function calls using names to objects (user, project, branch...)
  - create a function to fix file.extension handling
  - is it possible to remove all the menu = menu_bar() calls, by using context processors?
  - add user data to the context processor as well
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

