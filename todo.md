  - make sure usernames are alphanumeric only
  - add logging: http://damyanon.net/flask-series-logging/
  - add project_properties to be passed to jinja files, including for instance copyright
  - add more options to project, such as: language, title... (see sphinx's conf.py)
  - add user options, such as: language
  - add project options
  - add branch options
  - use one origin for the project and everyone clones from there (even master)
  - ability to add new file (possibly with template for name)
  - ability to rename file (possibly with template for name)
  - ability to remove file
  - user url_for for every url construction, including jinja
  - add common prefix to all routes (for serving on folder of domain). Or can this be done in Apache?
  - allow reviewer to continue editing without addressing merge requests
  - implement two-way merge, see https://github.com/lqc/google-diff-match-patch
  - use context processors to automatically add variables to templates
  - start using user data that is automatically passed to jinja instead of explicitly from render
  - create functions `read_file` and `write_file` to reduce use of `with codecs...`



  - implement comments and issues
  - bug in diff? see also https://github.com/lqc/google-diff-match-patch
  - give option for reviewer to delete branch on finishing merge

  - add ability to change language
  - update translation po files: http://stackoverflow.com/a/7497395
  - make a timeout for sphinx-build: http://stackoverflow.com/a/4825933
  - remove specific configurations from conf/conf.py, they should go to toml and be imported
  - implement submodules for javascript code,
    - https://github.com/lqc/google-diff-match-patch
    - https://github.com/sphinx-doc/sphinx/tree/master/sphinx/themes/bizstyle/static
    - https://github.com/mathjax/MathJax
