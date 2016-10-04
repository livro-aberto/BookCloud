  - propagate commits down the subtree and minimize updates
  - allow user to delete branch
  - add more presence of the database, such as when listing projects

  - bug in diff? see also https://github.com/lqc/google-diff-match-patch

  - use safe_join to avoid malicious filenames


  - is it possible to remove all the menu = menu_bar() calls, by using context processors?

  - add master and parent branches to menu bar?

  - replace all possible function calls using names to objects (user, project, branch...)
  - upload figures

  - add logging: http://damyanon.net/flask-series-logging/

  - create a function to fix file.extension handling
  - add template names for new files

  - add user data to the context processor as well

  - split the branch tree into active and inactive branches.
    only show the smallest tree that contains all the active
    then below show the full tree

  - implement delete project

  - ability to rename file (possibly with template for name)
  - ability to remove file


  - add user options, such as: language
  - add project options  (see sphinx's conf.py)
    - such as: url, language, title...
    - add project_properties to be passed to jinja files, including for instance copyright
    - fix conf path in sphinx (pointing to /home/gutosurrex...)
  - add branch options

  - implement comments and issues

  - make a timeout for sphinx-build: http://stackoverflow.com/a/4825933
  - implement submodules for javascript code,
    - https://github.com/lqc/google-diff-match-patch
    - https://github.com/sphinx-doc/sphinx/tree/master/sphinx/themes/bizstyle/static
    - https://github.com/mathjax/MathJax

  - fix BookCloud.wsgi to use a configuration value as path



