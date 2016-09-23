  - make a timeout for sphinx-build: http://stackoverflow.com/a/4825933
  - use gettext to translate BookCloud
  - make sure usernames are alphanumeric only
  - automate test using pytest
  - remove specific configurations from conf/conf.py, they should go to toml and be imported
  - add logging: http://damyanon.net/flask-series-logging/
  - add project_properties to be passed to jinja files, including for instance copyright
  - add more options to project, such as: language, title...
  (see sphinx's conf.py)
  - add user options, such as: language
  - add user/project options, such as: default reviewer and ability to change reviewer
  - ability to add new file (possibly with template for name)
  - ability to rename file (possibly with template for name)
  - ability to remove file
  - add common prefix to all routes (for serving on folder of domain). Or can this be done in Apache?
  - view other person's repo
  - implement comments and issues
  - bug in diff? see also https://github.com/lqc/google-diff-match-patch
  - allow reviewer to continue editing without addressing merge requests
  - implement two-way merge, see https://github.com/lqc/google-diff-match-patch
  - implement submodules for javascript code,
    - https://github.com/lqc/google-diff-match-patch
    - https://github.com/sphinx-doc/sphinx/tree/master/sphinx/themes/bizstyle/static
    - https://github.com/mathjax/MathJax
  - user url_for for every url construction, including jinja
  - use context processors to automatically add variables to templates
  - create functions read_file and write_file to reduce use of `with codecs...`
  - start using user data that is automatically passed to jinja instead of explicitly from render




