  - think about what should come first: commit or merge requests
  - allow user to delete branch
  - add more presence of the database, such as when listing projects

  - bug in diff? see also https://github.com/lqc/google-diff-match-patch

  - use safe_join to avoid malicious filenames


  - implement flask-babel:
    best tutorial:
      http://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-xiv-i18n-and-l10n
    more stuff:
      http://stackoverflow.com/a/9515968
      https://pythonhosted.org/Flask-Babel/
      http://jinja.pocoo.org/docs/dev/templates/#i18n-in-templates

  - split the branch tree into active and inactive branches.
    only show the smallest tree that contains all the active
    then below show the full tree

  - is it possible to remove all the menu = menu_bar() calls, by using context processors?

  - add master and parent branches to menu bar?

  - replace all possible function calls using names to objects (user, project, branch...)
  - upload figures
  - implement two-way merge, see https://github.com/lqc/google-diff-match-patch
  - allow reviewer to continue editing without addressing merge requests

  - add logging: http://damyanon.net/flask-series-logging/

  - create a function to fix file.extension handling
  - add template names for new files

  - use wtform to guarantee that names are well input (don't trust client browser for validation)

  - use context processors to automatically add variables to templates
  - start using user data that is automatically passed to jinja instead of explicitly from render
    is it already there? we could use the context processor as well

  - implement delete project

  - ability to rename file (possibly with template for name)
  - ability to remove file
  - add more options to project, such as: language, title... (see sphinx's conf.py)

  - add user options, such as: language
  - add project options
    - add project_properties to be passed to jinja files, including for instance copyright
    - fix conf path in sphinx (pointing to /home/gutosurrex...)
  - add branch options

  - ask in stackexchange if there is a way to access view arguments from jinja without passing them

  - implement comments and issues

  - make a timeout for sphinx-build: http://stackoverflow.com/a/4825933
  - implement submodules for javascript code,
    - https://github.com/lqc/google-diff-match-patch
    - https://github.com/sphinx-doc/sphinx/tree/master/sphinx/themes/bizstyle/static
    - https://github.com/mathjax/MathJax

  - fix BookCloud.wsgi to use a configuration value as path



