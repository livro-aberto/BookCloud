import os
import json
from os.path import isdir, isfile, join
import flask
from flask import render_template, render_template_string, request, redirect, url_for, Response, flash, Blueprint
from flask_user import login_required, UserManager, UserMixin, SQLAlchemyAdapter, current_user
from application import app, db, User, Project, Branch
import string
from shutil import copyfile
import git
from difflib import HtmlDiff

import codecs # deals with encoding better
import sphinx

import gettext

config_path = 'conf'

bookcloud = Blueprint('bookcloud', __name__, template_folder='templates',)

@app.before_first_request
def set_lang():
    language = app.config['LANGUAGE']
    lang = gettext.translation('messages', localedir='locale', languages=[language])
    lang.install(True)
    _ = lang.ugettext

def get_git(project, branch):
    repo_path = join('repos', project, branch, 'source')
    repo = git.Repo(repo_path)
    return repo.git

def load_json(path):
    with codecs.open(path, 'r', 'utf-8') as content_file:
        return json.loads(content_file.read())

def write_json(path, structure):
    with codecs.open(path, 'w', 'utf-8') as dest_file:
        dest_file.write(json.dumps(structure))

def get_merging(project, branch):
    merge_file_path = join('repos', project, branch, 'merging.json')
    if isfile(merge_file_path):
        return load_json(merge_file_path)

def std_menu(username):
    return [{'url': url_for('user.logout'), 'name': 'logout'},
            {'url': url_for('bookcloud.profile'), 'name': username}]

def get_requests(project, branch):
    git_api = get_git(project, branch)
    branches = string.split(git_api.branch())
    merged = string.split(git_api.branch('--merged'))
    unmerged = [item for item in branches if item not in merged]
    bar_menu = std_menu(current_user.username)
    if len(unmerged):
        return render_template('requests.html', project=project, branch=branch,
                               unmerged=unmerged, bar_menu=bar_menu)

def get_pendencies(project, branch, username):
    # user already has the repository?
    if username != get_branch_owner(project, branch):
        return None
    branch_repo_path = join('repos', project, branch)
    # if not isdir(branch_repo_path):
    #     flash(_('You need to clone this repository first'), 'error')
    #     return redirect(url_for(branches, project=project))
    # user is merging?
    merging = get_merging(project, branch)
    if merging:
        return redirect(url_for(merge, project=project, branch=branch, other=merging['branch']))
    # user has a pending request?
    requests = get_requests(project, branch)
    if requests:
        return requests
    # update from reviewer (if the user is not his own reviewer)
    if branch != 'master':
        origin_branch = get_branch_origin(project, branch)
        git_api = get_git(project, branch)
        git_api.fetch()
        git_api.merge('-s', 'recursive', '-Xours', 'origin/' + origin_branch)
        git_api.push('origin', branch)
        build(project, branch)

def config_repo(repo, user_name, email):
    config = repo.config_writer()
    config.set_value('user', 'email', email)
    config.set_value('user', 'name', user_name)

def create_project(project, user_name):
    # create a repository
    repo_path = join('repos', project, 'master/source')
    os.makedirs(repo_path)
    git.Repo.init(repo_path)
    repo = git.Repo(repo_path)
    config_repo(repo, user_name, user_name + '@example.com')
    copyfile('application/empty_repo/source/index.rst', join(repo_path, 'index.rst'))
    copyfile('application/empty_repo/.gitignore', join(repo_path, '.gitignore'))
    repo.index.add(['index.rst', '.gitignore'])
    repo.index.commit(_('Initial commit'))
    # add project to database
    user_id = User.query.filter(User.username == user_name).first().id
    new_project = Project(project, user_id)
    db.session.add(new_project)
    # add master branch to database
    db.session.commit()
    project_id = Project.query.filter_by(name=project).first().id
    origin_id = 1
    new_branch = Branch('master', project_id, origin_id, user_id)
    db.session.add(new_branch)
    db.session.commit()
    # updating branch's self reference
    new_branch = Branch.query.filter_by(project_id=project_id).first()
    new_branch.origin_id = new_branch.id
    db.session.commit()
    build(project, 'master')

def get_branch_owner(project, branch):
    project_id = Project.query.filter_by(name=project).first().id
    return Branch.query.filter_by(project_id=project_id, name=branch).first().owner.username

def get_sub_branches(project, branch):
    project_id = Project.query.filter_by(name=project).first().id
    branch_id = Branch.query.filter_by(project_id=project_id, name=branch).first().id
    children_list = Branch.query.filter_by(project_id=project_id, origin_id=branch_id)
    answer = {}
    #if children_list.first() == None:
    #    return answer
    for child in children_list:
        if child.name != 'master':
            print(child.name)
            answer[child.name] = get_sub_branches(project, child.name)
    #return { 'name': branch, 'subtree': answer }
    return answer

def get_branch_origin(project, branch):
    project_id = Project.query.filter_by(name=project).first().id
    origin_id = Branch.query.filter_by(project_id=project_id, name=branch).first().origin_id
    return Branch.query.filter_by(id=origin_id).first().name

def create_branch(project, origin, branch, user_name):
    # Clone repository from a certain origin branch
    branch_path = join('repos', project, branch, 'source')
    origin_repo = git.Repo(join('repos', project, origin, 'source'))
    origin_repo.clone(os.path.abspath(join(os.getcwd(), branch_path)), branch=origin)
    branch_repo = git.Repo(os.path.abspath(join(os.getcwd(), branch_path)))
    config_repo(branch_repo, user_name, user_name + '@here.com')
    git_api = branch_repo.git
    git_api.checkout('HEAD', b=branch)

    project_id = Project.query.filter_by(name=project).first().id
    origin_id = Branch.query.filter_by(project_id=project_id, name=origin).first().id
    owner_id = User.query.filter_by(username=user_name).first().id
    new_branch = Branch(branch, project_id, origin_id, owner_id)

    db.session.add(new_branch)
    db.session.commit()
    #properties = {'origin': origin}
    #write_json(join('repos', project, branch, 'properties.json'), properties)
    build(project, branch)

def build(project, branch):
    # Replace this terrible implementation
    config_path = 'conf'
    source_path = join('repos', project, branch, 'source')
    build_path = join('repos', project, branch, 'build/html')
    # args = ['-a', '-c conf']
    # if sphinx.build_main(args + ['source/', 'build/html/']):
    #     os.chdir(previous_wd)
    #     return False
    # os.chdir(previous_wd)
    # return True
    command = 'sphinx-build -c ' + config_path + ' ' + source_path + ' ' + build_path
    os.system(command)
    return True

def build_latex(project, branch):
    # Replace this terrible implementation
    config_path = 'conf'
    source_path = join('repos', project, branch, 'source')
    build_path = join('repos', project, branch, 'build/latex')
    command = 'sphinx-build -a -b latex -c ' + config_path + ' ' + source_path + ' ' + build_path
    os.system(command)
    return True

@login_required
@bookcloud.route('/<project>/branches', methods = ['GET', 'POST'])
def branches(project):
    path = join('repos', project)
    branches = [d for d in os.listdir(path) if isdir(join(path, d))]
    if (current_user.is_authenticated):
        bar_menu = std_menu(current_user.username)
    else:
        bar_menu = [{'url': url_for('user.login'), 'name': 'login'}]
    text = {'title': _('Project branches')}
    tree = { 'master': get_sub_branches(project, 'master') }
    print(tree)
    return render_template('branches.html', project=project, branches=branches, tree=tree,
                           text=text, bar_menu=bar_menu)

@login_required
@bookcloud.route('/<project>/<branch>/accept/<path:filename>')
def accept(project, branch, filename):
    if current_user.username != get_branch_owner(project, branch):
        flash(_('You are not the owner of this branch'), 'error')
        return redirect(url_for('.view', project=project, branch=branch, filename='index.html'))
    merging = get_merging(project, branch)
    if not merging:
        flash(_('You are not merging a submission'), 'error')
        return redirect(url_for('.view', project=project, branch=branch, filename='index.html'))
    if not filename in merging['modified']:
        flash('File ' + filename + ' is not being reviewed', 'error')
        return redirect(url_for('.view', project=project, branch=branch, filename='index.html'))
    merging['modified'].remove(filename)
    merging['reviewed'].append(filename)
    merge_file_path = join('repos', project, branch, 'merging.json')
    write_json(merge_file_path, merging)
    return redirect(url_for('.merge', project=project, branch=branch, other=merging['branch']))

@login_required
@bookcloud.route('/<project>/<branch>/finish')
def finish(project, branch):
    if current_user.username != get_branch_owner(project, branch):
        flash(_('You are not the owner of this branch'), 'error')
        return redirect(url_for('.view', project=project, branch=branch, filename='index.html'))
    merging = get_merging(project, branch)
    if not merging:
        flash(_('You are not merging!'), 'error')
        return redirect(url_for('.view', project=project, branch=branch, filename='index.html'))
    if len(merging['modified']):
        flash(_('You still have unreviewed files'), 'error')
        return redirect(url_for('.view', project=project, branch=branch, filename='index.html'))
    git_api = get_git(project, branch)
    git_api.commit('-m', 'Merge ' + merging['branch'])
    merge_file_path = join('repos', project, branch, 'merging.json')
    os.remove(merge_file_path)
    build(project, branch)
    flash(_('You have finished merging _%s') % merging['branch'], 'info')
    return redirect(url_for('.view', project=project, branch=branch, filename='index.html'))

@bookcloud.route('/<project>/<branch>/view/<path:filename>')
def view(project, branch, filename):
    filename, file_extension = os.path.splitext(filename)
    if file_extension == '':
        file_extension = '.html'
    user_repo_path = join('repos', project, branch,
                          'build/html', filename + file_extension)
    if (current_user.is_authenticated):
        pendencies = get_pendencies(project, branch, current_user.username)
        if pendencies:
            return pendencies
        bar_menu = [{'url': url_for('user.logout'), 'name': 'logout'},
                    {'url': url_for('.edit', project=project, branch=branch,filename=filename),
                     'name': 'edit'},
                    {'url': url_for('bookcloud.profile'), 'name': current_user.username}]
    else:
        bar_menu = [{'url': url_for('user.login'), 'name': 'login'}]
    build(project, branch)
    with codecs.open(user_repo_path, 'r', 'utf-8') as content_file:
        content = content_file.read()
    return render_template_string(content, bar_menu=bar_menu, render_sidebar=True)

@login_required
@bookcloud.route('/<project>/<branch>/save/<path:filename>', methods = ['GET', 'POST'])
def save(project, branch, filename):
    if current_user.username != get_branch_owner(project, branch):
        flash(_('You are not the owner of this branch'), 'error')
        return redirect(url_for('.view', project=project, branch=branch, filename='index.html'))
    pendencies = get_pendencies(project, branch, current_user.username)
    if pendencies:
        return pendencies
    filename, file_extension = os.path.splitext(filename)
    user_repo_path = join('repos', project, branch)
    if request.method == 'POST':
        with codecs.open(join(user_repo_path, 'source', filename + '.rst'), 'w') as dest_file:
            dest_file.write(request.form['code'].encode('utf8'))
    repo = git.Repo(join(user_repo_path, 'source'))
    repo.index.add([filename + '.rst'])
    repo.index.commit(_('Change in %s by %s') % (filename, current_user.username))
    git_api = repo.git
    origin = get_branch_origin(project, branch)
    if branch != origin:
        git_api.push('origin', branch)
        flash(_('Page submitted to _%s') % origin, 'info')
    build(project, branch)
    return redirect(url_for('.view', project=project, branch=branch, filename='index.html'))

@login_required
@bookcloud.route('/<project>/<branch>/edit/<path:filename>', methods = ['GET', 'POST'])
def edit(project, branch, filename):
    if current_user.username != get_branch_owner(project, branch):
        flash(_('You are not the owner of this branch'), 'error')
        return redirect(url_for('.clone', project=project, branch=branch))
    pendencies = get_pendencies(project, branch, current_user.username)
    if pendencies:
        return pendencies
    branch_source_path = join('repos', project, branch, 'source', filename + '.rst')
    branch_html_path = join('repos', project, branch, 'build/html', filename + '.html')
    if request.method == 'POST':
        with codecs.open(branch_source_path, 'w') as dest_file:
            dest_file.write(request.form['code'].encode('utf8'))
    build(project, branch)
    with codecs.open(branch_source_path, 'r', 'utf-8') as content_file:
        rst = content_file.read()
    with codecs.open(branch_html_path, 'r', 'utf-8') as content_file:
        doc = render_template_string(content_file.read(), barebones=True)
    text = {'title': _('Edit:'), 'image': _('Image'), 'math': _('Math mode'),
            'sections': _('Sections'), 'style': _('Style'),
            'cancel': _('Cancel'), 'preview': _('Preview'), 'submit': _('Submit')}
    return render_template('edit.html', doc=doc, rst=rst, filename=filename, branch=branch,
                           project=project, text=text, render_sidebar=False)

@login_required
@bookcloud.route('/<project>/<branch>/review/<path:filename>')
def review(project, branch, filename):
    return "Not implemented yet..."

@login_required
@bookcloud.route('/<project>/<branch>/diff/<path:filename>')
def diff(project, branch, filename):
    if current_user.username != get_branch_owner(project, branch):
        flash(_('You are not the owner of this branch'), 'error')
        redirect(url_for('.view', project=project, branch=branch, filename='index.html'))
    merging = get_merging(project, branch)
    if not merging:
        flash(_('You are not merging'), 'error')
        redirect(url_for('.project', project=project))
    bar_menu = std_menu(current_user.username)
    differ = HtmlDiff()
    filename, file_extension = os.path.splitext(filename)
    branch_source_path = join('repos', project, branch, 'source', filename + '.rst')
    with codecs.open(branch_source_path, 'r', 'utf-8') as content_file:
        new = string.split(content_file.read(), '\n')
    git_api = get_git(project, branch)
    old = string.split(git_api.show('master:' + filename + file_extension), '\n')
    diff = differ.make_table(new, old)
    diff = string.replace(diff, 'nowrap="nowrap"', '')
    text = {'title': _(' has suggested a change to the file: '),
            'instructions': _('The proposed version is on the left, while the old version is on the right.')}
    return render_template('diff.html',  project=project, other=merging['branch'],
                           diff=diff, filename=filename + file_extension, branch=branch,
                           text=text, bar_menu=bar_menu)

@login_required
@bookcloud.route('/<project>/<branch>/merge/<other>')
def merge(project, branch, other):
    merging = get_merging(project, branch)
    if not merging:
        git_api = get_git(project, branch)
        git_api.merge('--no-commit', '--no-ff', '-s', 'recursive', '-Xtheirs', other)
        modified = string.split(git_api.diff('HEAD', '--name-only'))
        merging = {'branch': other, 'modified': modified, 'reviewed': []}
        write_json(join('repos', project, branch, 'merging.json'), merging)
    bar_menu = std_menu(current_user.username)
    text = {'title': _('Merging from _'), 'unseen': _('Modifications not yet reviewed'),
            'review': _('Review file'), 'accept': _('Accept suggestions'), 'view': _('View differences'),
            'reviewed': _('Changes reviewed'), 'finally': _('You have finished all the reviews'),
            'finish': _('Finish merge')}
    return render_template('merge.html', project=project, modified=merging['modified'],
                           reviewed=merging['reviewed'], branch=branch, other=other,
                           text=text, bar_menu=bar_menu)

@bookcloud.route('/<project>')
def index(project):
    text = {'title': _('List of branches')}
    if (current_user.is_authenticated):
        bar_menu = std_menu(current_user.username)
    else:
        bar_menu = [{'url': url_for('user.login'), 'name': 'login'}]
    return render_template('branches.html', text=text, project=project, bar_menu=bar_menu)

@bookcloud.route('/')
def projects():
    path = 'repos'
    projects = [d for d in os.listdir(path) if isdir(join(path, d))]
    if current_user.is_authenticated:
        bar_menu = std_menu(current_user.username)
    else:
        bar_menu = [{'url': url_for('user.login'), 'name': 'login'}]
    text = {'title': _('Projects list'), 'download': _('Download'), 'new': _('Create new project')}
    return render_template('projects.html', projects=projects, bar_menu=bar_menu,
                           text=text, copyright='CC-BY-SA-NC')

@bookcloud.route('/profile')
def profile():
    if not current_user.is_authenticated:
        redirect (url_for('user.login'))
    bar_menu = std_menu(current_user.username)
    return render_template('profile.html', username=current_user.username, bar_menu=bar_menu)

@bookcloud.route('/new', methods = ['GET', 'POST'])
def new():
    if not current_user.is_authenticated:
        flash(_('You need to be logged in to create a new project'), 'error')
        return redirect(url_for('user.login'))
    bar_menu = std_menu(current_user.username)
    if request.method == 'POST':
        user_repo_path = join('repos', request.form['project'])
        if os.path.isdir(user_repo_path):
            flash(_('This project name already exists'), 'error')
        else:
            create_project(request.form['project'], current_user.username)
            flash(_('Project created successfuly!'), 'info')
            return redirect(url_for('.projects'))
    text = {'title': _('Create new project'), 'submit': 'Submit'}
    return render_template('new.html', text=text, bar_menu=bar_menu)

@bookcloud.route('/<project>/<branch>/newfile', methods = ['GET', 'POST'])
def newfile(project, branch):
    if not current_user.is_authenticated:
        flash(_('You need to be logged in to create a new file'), 'error')
        return redirect(url_for('.login'))
    bar_menu = std_menu(current_user.username)
    if request.method == 'POST':
        filename, file_extension = os.path.splitext(request.form['filename'])
        if file_extension == '':
            file_extension = '.rst'
        file_path = join('repos', project, branch, 'source', filename + file_extension)
        if os.path.isfile(file_path):
            flash(_('This file name name already exists'), 'error')
        else:
            file = open(file_path, 'w+')
            file.write('=' * len(filename) + '\n' + filename + '\n' + '=' * len(filename) + '\n')
            flash(_('File created successfuly!'), 'info')
            build(project, branch)
            return redirect(url_for('.view', project=project, branch=branch, filename='index.html'))
    text = {'title': _('Create new file'), 'submit': 'Submit'}
    return render_template('newfile.html', project=project, branch=branch,
                           text=text, bar_menu=bar_menu)

@bookcloud.route('/<project>/<branch>/clone', methods = ['GET', 'POST'])
def clone(project, branch):
    if not current_user.is_authenticated:
        flash(_('You need to be logged in to clone a project'), 'error')
        return redirect(url_for('user.login'))
    bar_menu = std_menu(current_user.username)
    if request.method == 'POST':
        new_repo_path = join('repos', project, request.form['name'])
        if os.path.isdir(new_repo_path):
            flash(_('This branch name already exists'), 'error')
            return redirect(url_for('.clone', project=project, branch=branch))
        else:
            new_branch = request.form['name']
            create_branch(project, branch, new_branch, current_user.username)
            flash(_('Project cloned successfuly!'), 'info')
            return redirect(url_for('.view', project=project, branch=new_branch, filename='index.html'))
    path = join('repos', project)
    branches = [d for d in os.listdir(path) if isdir(join(path, d))]
    text = {'title': _('Create your own branch of this project'), 'submit': 'Submit',
            'name': _('Choose branch name')}
    return render_template('clone.html', project=project, branch=branch,
                           branches=branches, text=text, bar_menu=bar_menu)

@bookcloud.route('/<project>/<branch>/pdf')
def pdf(project, branch):
    if (current_user.is_authenticated):
        build_path = os.path.abspath(join('repos', project, branch, 'build/latex'))
    else:
        build_path = os.path.abspath(join('repos', project, branch, 'build/latex'))
    build_latex(project, branch)
    command = '(cd ' + build_path + '; pdflatex -interaction nonstopmode linux.tex > /tmp/222 || true)'
    os.system(command)
    return flask.send_from_directory(build_path, 'linux.pdf')

@bookcloud.route('/<project>/comment_summary/<path:filename>')
def comment_summary(project, filename):
    return 'Comments from ' + filename

@bookcloud.route('/<project>/<action>/_images/<path:filename>')
@bookcloud.route('/edit/<project>/images/<path:filename>', methods = ['GET'])
def get_tikz(project, action, filename):
    images_path = join('repos', project, current_user.username, 'build/html/_images')
    return flask.send_from_directory(os.path.abspath(images_path), filename)

@bookcloud.route('/<project>/<action>/_static/<path:filename>')
def get_static(project, action, filename):
    if (current_user.is_authenticated):
        user_repo_path = join('repos', project, current_user.username)
    else:
        user_repo_path = join('repos', project, get_creator(project))
    return flask.send_from_directory(os.path.abspath(join(user_repo_path, 'build/html/_static/')), filename)

@bookcloud.route('/_static/<path:filename>')
def get_global_static(filename):
    return flask.send_from_directory(os.path.abspath('conf/biz/static/'), filename)

@bookcloud.route('/_sources/<path:filename>')
def show_source(filename):
    sources_path = join('repos', current_user.username, 'build/html/_sources', filename)
    with codecs.open(sources_path, 'r', 'utf-8') as content_file:
        content = content_file.read()
    return Response(content, mimetype='text/txt')

@bookcloud.route('/<project>/images/<path:filename>')
def get_image(project, filename):
    return flask.send_from_directory(os.path.abspath('repos/' + project + '/images'), filename)

@bookcloud.route('/<project>/<branch>/view/genindex.html')
def genindex(project, branch):
    return redirect(url_for('.view', project=project, branch=branch, filename='index.html'))

@bookcloud.route('/login')
def login():
    return redirect(url_for('user.login'))

@bookcloud.route('/logout')
def logout():
    return redirect(url_for('user.logout'))

@bookcloud.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@bookcloud.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

# @bookcloud.errorhandler(403)
# def page_forbidden(e):
#     return render_template('403.html'), 500


