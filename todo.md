# Urgent:

  - in discussions:
    - put example tags to help user start typing (using random elements from sql)
    - put link to view discussions and to add discussion on that topic
  - implement follow thread
  - implement tags for labels (remove the file from the name?)
  - make security improvements on sphinx:
    - disallow raw html
      read the documentation for more
      http://docutils.sourceforge.net/docs/ref/rst/directives.html#raw-data-pass-through

  - parse sphinx
    https://stackoverflow.com/questions/10766609/extract-field-list-from-restructuredtext/10782270#10782270
    https://stackoverflow.com/questions/11302885/parse-sphinx-like-documentation
  - improve search labels?

        from docutils.parsers import rst
        settings = docutils.frontend.OptionParser(
            components=(docutils.parsers.rst.Parser,)
            ).get_default_values()

        document = docutils.utils.new_document('', settings)

        # here one can use load_file
        with codecs.open('index.txt', 'r', 'utf-8') as file:
            data = file.read()

        rst.Parser().parse(data,document)

        data = document.asdom().toxml()
        y = BeautifulSoup(data)
        q = set([t for t in y.find_all('target')])

# Restructure code:

  - organize the use of paths
  - create classes to handle common code
  - split view.py into services

# Features:

  - user experience. Read book:

        https://en.wikibooks.org/wiki/Usability_for_Nerds/Print_version
  - exercises. use javascript for electronic activities:

        https://jsxgraph.uni-bayreuth.de/wiki/index.php/Category:Examples

  - intensify use of include in sphinx:

        http://docutils.sourceforge.net/docs/ref/rst/directives.html#miscellaneous
  - consider support for MathBook XML:

        http://mathbook.pugetsound.edu/index.html

  - consider interfacing with redmine:

        https://python-redmine.com/

  - make site usable when javascript is disabled.
  - use ajax and sql queries for tag completion in textext
    read also:

        https://github.com/alexgorbatchev/jquery-textext/issues/9

  - remove mathjax from where it is not needed, for speed
  (priority)
  - create master admin view with:
    - manage named tags...
  - implement "steal branch" from parent owner
  - comments:
    - implement like (is unicode symbol the &#128077;?)
    - link to view file in thread tags
    - make comments hidden, with a show toggle button, so that only thread titles are shown
  - commit text below commit message view
  - upload figures
    - use safe_join to avoid malicious filenames
    - size of figures (thumbnail for html, hd for pdf...)

  (medium)
  - more object types: discussion, issue, room,...
    - column for access rights? private (only owner), moderators of project, logged, public...
    - column for arbitrary data: json structure that is specific of the object type
  - radio button with commit author in commit view (add external authors to database?)
  - add template names for new files
  - implement delete project

  - implement other file types (besides rst). For this:
    - implement jinja for view<extension>.html
    - implement jinja for edit<extension>.html
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

  - organize view.py into different files:
    - git functions
    - helper functions
    - user profile (delete, change password...)
        Última formação
          - Nenhuma
          - Fundamental
          - Médio
          - Superior
          - Mestrado
          - Doutorado

        Estado
          - RJ
          - SP...
        Capital (booleana)

        Profissão
          - Estudante ensino fundamental
          - Estudante ensino médio
          - Professor ensino fundamental I
          - Professor ensino fundamental II
          - Professor ensino médio
          - Professor ensino superior
          - Outros

        Sabe LaTeX (booleana)
        Sabe HTML (booleana)
        Sabe Programar (booleana)
        Sabe Python (booleana)
        Sabe Javascript (booleana)
        Sabe faze figuras (booleana)
        Sabe editar vídeos (booleana)

        Já participou da organização de evento acadêmico (booleana)

        Quantas horas gostaria de dedicar por semana ao projeto?
          - Não sei
          - Adorei a ideia, mas não quero ser solicitado
          - Até 2 horas
          - Entre 2 e 5 horas
          - Entre 5 e 10 horas
          - Mais de 10 horas
        Como você quer colaborar?
          - Gostaria de colaborar fazendo sugestões acadêmicas nos materiais produzidos
          - Gostaria de colaborar aplicando o material na minha sala de aula
          - Gostaria de colaborar implemento as sugestões de outros usuários ou da equipe na plataforma
          - Gostaria de colaborar diagramação do texto em LaTeX
          - Gostaria de colaborar mantendo o site, implementando modificações da plataforma programando
          - Gostaria de colaborar organizando oficinas de professores
          - Gostaria de colaborar fazendo figuras para o livro
          - Gostaria de colaborar produzindo ou editando vídeos
      - organize views:
      - main: home, new, project, branch, clone, newfile, requests, finish, commit, review, diff, accept
      - extension specific: pdf, view, edit, merge
      - comments: comments, newthread, newcomment, deletethread, deletecomment
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
