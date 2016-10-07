# Urgent:

  - propagate commits down the subtree and minimize updates
  - allow user to delete branch (setup expiration time for branches?)
  - add more presence of the database, such as when listing projects?

# Features:

  (priority)
  - commit text below commit message
  - upload figures
    - use safe_join to avoid malicious filenames
  - implement comments and issues
  - view commits in branch or project page:
    - git log --pretty="format:%h %an" --graph
    - http://ricostacruz.com/cheatsheets/git-log-format.html

  (medium)
  - ability to rename file (possibly with template for name)
  - ability to remove file
  - add template names for new files
  - implement delete project
  - make a timeout for sphinx-build: http://stackoverflow.com/a/4825933

# Bugs:

  - bug in diff? see also https://github.com/lqc/google-diff-match-patch
  - add logging: http://damyanon.net/flask-series-logging/

# Interface:

  (important)
  - add branch options including:
    modifications, diff with master, owner, subtree, requests, latest commits...

  - add master and parent branches to menu bar?
  - split the branch tree into active and inactive branches.
    only show the smallest tree that contains all the active
    then below show the full tree

  - add user options, such as: language
  - add project options  (see sphinx's conf.py)
    - such as: url, language, title...
    - add project_properties to be passed to jinja files, including for instance copyright
    - fix conf path in sphinx (pointing to /home/gutosurrex...)

# Organization of code:

  - find patterns in functions, such as: pendencies, is merging...
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



