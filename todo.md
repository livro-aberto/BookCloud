  - make sure usernames, project names and branch names are alphanumeric only
  - ability to add new file (possibly with template for name)
  - add common prefix to all routes (for serving on folder of domain). Or can this be done in Apache?

  - implement two-way merge, see https://github.com/lqc/google-diff-match-patch
  - allow reviewer to continue editing without addressing merge requests
  - use one origin for the project and everyone clones from there (even master)
  - add project_properties to be passed to jinja files, including for instance copyright
  - use context processors to automatically add variables to templates
  - start using user data that is automatically passed to jinja instead of explicitly from render
  - create functions `read_file` and `write_file` to reduce use of `with codecs...`

  - ability to rename file (possibly with template for name)
  - ability to remove file
  - add more options to project, such as: language, title... (see sphinx's conf.py)
  - add logging: http://damyanon.net/flask-series-logging/
  - add user options, such as: language
  - add project options
  - add branch options

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
