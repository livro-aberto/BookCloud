from flask import Blueprint, request, render_template, url_for, flash, redirect
from flask_user import login_required

from flask_user import login_required, current_user
from flask_babel import gettext as _
from flask_mail import Message
from sqlalchemy import or_, desc

from application import db, app, limiter, mail
from application.users import User
from application.threads import *
from application.tools import load_file

from ..utils import menu_bar
from ..models import Project


import json
import re
import urllib
import os
from os.path import join, isfile, splitext
from datetime import datetime

threads = Blueprint('threads', __name__, url_prefix='/threads')

#@limiter.exempt
#@threads.route('/<project>/tagsthreads/<filetag>')
#def tagthreads(project, filetag):
#    # Find threads with a certain filetag
#    menu = menu_bar(project)
#    project_id = Project.query.filter_by(name=project).first().id
#    threads = (Thread.query.join(File_Tag)
#               .filter(File_Tag.filename.like('%' + filetag + '%'))
#               .filter(Thread.project_id==project_id)
#               .order_by(desc(Thread.posted_at)))
#    return render_template('comments.html', menu=menu, threads=threads,
#                           show_discussion=True)

@threads.route('/<project>/search_comments', methods = ['GET', 'POST'])
def search_comments(project):
    menu = menu_bar(project)
    project = Project.query.filter_by(name=project).first_or_404()
    form = CommentSearchForm(request.form)
    if request.method == 'POST' and form.validate():
        if not form.search.data:
            form.search.data = ""
        threads = (Thread.query.filter(Thread.project==project)
                   .join(Comment)
                   .filter(Comment.thread_id==Thread.id)
                   .filter(or_(Comment.content.like('%' + form.search.data + '%'),
                               Thread.title.like('%' + form.search.data + '%')))
                   .order_by(desc(Thread.posted_at))
                   .limit(100))
    else:
        threads = (Thread.query
                   .filter_by(project=project)
                   .order_by(desc(Thread.posted_at))
                   .limit(100))
    return render_template('search_comments.html', menu=menu, threads=threads,
                           form=form, show_discussion=True)

@threads.route('/<project>/newthread', methods = ['GET', 'POST'])
@login_required
def newthread(project):
    menu = menu_bar(project)
    project_id = Project.query.filter_by(name=project).first().id
    filters = {}
    default = {}
    filters["usertags"] = json.dumps([u.username for u in User.query.all()])
    master_path = join('repos', project, 'master', 'source')
    label_list = []
    for f in os.listdir(master_path):
        if (isfile(join(master_path, f)) and f[0] != '.'):
            data = load_file(join(master_path, f))
            label_list.extend([splitext(f)[0] + '#' + l
                               for l in re.findall(r'^\.\. _([a-z\-]+):\s$', data, re.MULTILINE)])
    filters["filetags"] = json.dumps(label_list)
    #    form.filetags.choices = [(splitext(f)[0], splitext(f)[0])
    #                             for f in os.listdir(master_path)
    #                             if isfile(join(master_path, f)) and f[0] != '.']
    if request.args.get('filetags', ''):
        default["filetags"] = json.dumps([request.args.get('filetags', '')])
    else:
        default["filetags"] = [""]
    filters["namedtags"] = json.dumps([t.name for t in Named_Tag.query.filter_by(project_id=project_id).all()])

    if request.method == 'POST':

        if ((request.form["title"] == "") or (request.form["firstcomment"] == "")):
            # Trying to recover when one entry was invalid
            # form.firstcomment.default = request.form['firstcomment']
            # form.title.default = request.form['title']
            # form.freetags.default = request.form['freetags']
            return render_template('newthread.html', filters=filters, default=default,
                                   menu=menu, show_discussion=False)
        else:
            #owner = User.get_by_name(current_user.username)
            owner = User.query.filter_by(username=current_user.username).first()
            # add thread
            new_thread = Thread(request.form['title'],
                                owner.id,
                                project_id,
                                request.form['flag'],
                                datetime.utcnow())
            db.session.add(new_thread)
            db.session.commit()
            # add first comment
            new_comment = Comment('000000:',
                                  new_thread.id,
                                  owner.id,
                                  request.form['firstcomment'],
                                  datetime.utcnow())
            db.session.add(new_comment)
            # add user tags
            for user in json.loads(request.form['usertags']):
                db.session.flush()
                user = User.query.filter_by(username=user).first()
                #new_usertag = User_Tag(new_thread.id, user_id)
                new_thread.user_tags.append(user)
                db.session.commit()#session.add(new_usertag)
            # add file tags
            for file in json.loads(request.form['filetags']):
                new_filetag = File_Tag(new_thread.id, file)
                db.session.add(new_filetag)
            # add named tags
            for tag in json.loads(request.form['namedtags']):
                db.session.flush()
                namedtag = Named_Tag.query.filter_by(project_id=project_id, name=tag).first()
                new_thread.custom_tags.append(namedtag)#new_namedtag = Custom_Tag(new_thread.id, namedtag_id)
                db.session.commit()#add(new_namedtag)
            # add free tags
            for freetag in filter(None, re.findall(r"[\w']+", request.form['freetags'])):
                new_freetag = Free_Tag(new_thread.id, freetag)
                db.session.add(new_freetag)

            db.session.commit()
            # send emails
            if not app.config['TESTING']:
                with mail.connect() as conn:
                    message_head = _('Thread: ') + request.form['title'] + '\n' +\
                                   _('Project: ') + project + '\n' +\
                                   _('Owner: ') + owner.username + '\n' +\
                                   _('Type: ') + request.form['flag'] + '\n' +\
                                   _('Created at: ') + str(datetime.utcnow()) + '\n' +\
                                   _('Contents:') + '\n\n'
                    links = _('To comment on this thread: ') +\
                            url_for('threads.newcomment',
                                    project=project,
                                    thread_id = new_thread.id,
                                    _external = True)
                    for user in json.loads(request.form['usertags']):
                        user_obj = User.query.filter_by(username=user).first()
                        message = message_head + request.form['firstcomment'] + '\n\n' + links
                        subject = _('Thread: ') + request.form['title']
                        msg = Message(recipients=[user_obj.email],
                                      body=message,
                                      subject=subject)
                        conn.send(msg)

            flash(_('New thread successfully created'), 'info')
            if 'return_url' in request.args:
                return redirect(urllib.unquote(request.args['return_url']))

    return render_template('newthread.html', filters=filters, default=default,
                           menu=menu, show_discussion=False)

@threads.route('/<project>/editthread/<thread_id>', methods = ['GET', 'POST'])
@login_required
def editthread(project, thread_id):
    menu = menu_bar(project)
    project_id = Project.query.filter_by(name=project).first().id
    thread_obj = Thread.query.filter_by(id=thread_id).first()
    if (current_user.username != thread_obj.owner.username and
        current_user.username != get_branch_owner(project, 'master')):
        flash(_('You are not allowed to edit this thread'), 'error')
        return redirect(url_for('bookcloud.project', project=project))
    form = ThreadForm(request.form)
    form.title.default = thread_obj.title
    form.flag.default = thread_obj.flag
    form.usertags.choices = [(u.username, u.username) for u in User.query.all()]
    form.usertags.default = [t.username for t in thread_obj.user_tags]# User_Tag.query.filter_by(thread_id=thread_id).all()]
    master_path = join('repos', project, 'master', 'source')
    label_list = []
    for f in os.listdir(master_path):
        if (isfile(join(master_path, f)) and f[0] != '.'):
            data = load_file(join(master_path, f))
            label_list.extend([(splitext(f)[0] + '#' + l, splitext(f)[0] + '#' + l)
                               for l in re.findall(r'^\.\. _([a-z\-]+):\s$', data, re.MULTILINE)])
    form.filetags.choices = label_list
    # form.filetags.choices = [(splitext(f)[0], splitext(f)[0])
    #                          for f in os.listdir(master_path)
    #                          if isfile(join(master_path, f)) and f[0] != '.']
    form.filetags.default = [t.filename for t in File_Tag.query.filter_by(thread_id=thread_id).all()]
    form.namedtags.choices = [(t.name, t.name) for t in Named_Tag.query.filter_by(project_id=project_id).all()]
    form.freetags.default = ', '.join([t.name for t in Free_Tag.query.filter_by(thread_id=thread_id).all()])

    if request.method == 'POST':
        if form.validate():
            owner = User.query.filter_by(username=current_user.username).first()
            # modify thread
            thread_obj.title = request.form['title']
            thread_obj.flag = request.form['flag']
            db.session.commit()
            # clear previous tags
            thread_obj.user_tags = []
            File_Tag.query.filter_by(thread_id=thread_id).delete()
            thread_obj.named_tags = []#Custom_Tag.query.filter_by(thread_id=thread_id).delete()
            Free_Tag.query.filter_by(thread_id=thread_id).delete()
            db.session.commit()
            # add user tags
            for user in request.form.getlist('usertags'):
                db.session.flush()
                user = User.query.filter_by(username=user).first()
                thread_obj.user_tags.append(user)
                db.session.commit()
            # add file tags
            for file in request.form.getlist('filetags'):
                new_filetag = File_Tag(thread_id, file)
                db.session.add(new_filetag)
            # add named tags
            for tag in request.form.getlist('namedtags'):
                db.session.flush()
                namedtag_id = Named_Tag.query.filter_by(project_id=project_id, name=tag).first().id
                new_namedtag = Custom_Tag(thread_id, namedtag_id)
                db.session.add(new_namedtag)
            # add free tags
            for freetag in filter(None, re.findall(r"[\w']+", request.form['freetags'])):
                new_freetag = Free_Tag(thread_id, freetag)
                db.session.add(new_freetag)

            db.session.commit()

            flash(_('Thread successfully modified'), 'info')
            if 'return_url' in request.args:
                return redirect(urllib.unquote(request.args['return_url']))
        else:
            form.title.default = request.form['title']
            form.freetags.default = request.form['freetags']

    form.process()
    return render_template('editthread.html', menu=menu, form=form)


@threads.route('/<project>/newcomment/<thread_id>', methods = ['GET', 'POST'])
@threads.route('/<project>/newcomment/<thread_id>/<parent_lineage>', methods = ['GET', 'POST'])
@login_required
def newcomment(project, thread_id, parent_lineage=''):
    menu = menu_bar(project)
    form = NewCommentForm(request.form)

    if request.method == 'POST':
        if form.validate():
            project_id = Project.query.filter_by(name=project).first().id
            owner = User.query.filter_by(username=current_user.username).first()
            siblings_pattern = parent_lineage + '%'
            decend_comments = (Comment.query.filter(Comment.thread_id==thread_id)
                               .filter(Comment.lineage.like(siblings_pattern)).all())
            number_siblings = len(decend_comments)
            new_comment_lineage = parent_lineage + format(number_siblings, '06X') + ':'
            new_comment = Comment(new_comment_lineage,
                                  thread_id,
                                  owner.id,
                                  request.form['comment'],
                                  datetime.utcnow())
            db.session.add(new_comment)
            db.session.commit()
            # send emails
            if not app.config['TESTING']:
                with mail.connect() as conn:
                    thread = Thread.query.filter_by(id=thread_id).first()
                    list_of_users = [ tag.username for tag in thread.user_tags]#User_Tag.query.filter_by(thread_id=thread_id) ]
                    message_head = _('Thread: ') + thread.title + '\n' +\
                                   _('Project: ') + project + '\n' +\
                                   _('Author: ') + owner.username + '\n' +\
                                   _('Type: ') + thread.flag + '\n' +\
                                   _('Created at: ') + str(datetime.utcnow()) + '\n' +\
                                   _('Contents:') + '\n\n'
                    links = _('To reply to this comment follow: ') +\
                            url_for('threads.newcomment',
                                    project=project,
                                    thread_id=thread.id,
                                    parent_lineage=new_comment_lineage,
                                    _external=True)
                    for user in list_of_users:
                        user_obj = User.query.filter_by(username=user).first()
                        message = message_head + request.form['comment'] + '\n\n' + links
                        subject = _('Thread: ') + thread.title
                        msg = Message(recipients=[user_obj.email],
                                      body=message,
                                      subject=subject)
                        conn.send(msg)

            flash(_('New comment successfully created'), 'info')
            if 'return_url' in request.args:
                return redirect(urllib.unquote(request.args['return_url']))
        else:
            form.comment.default = request.form['comment']

    threads = Thread.query.filter_by(id=thread_id).order_by(desc(Thread.posted_at))
    form.process()
    return render_template('newcomment.html', menu=menu, form=form, threads=threads)

@threads.route('/<project>/editcomment/<comment_id>', methods = ['GET', 'POST'])
@login_required
def editcomment(project, comment_id):
    menu = menu_bar(project)
    form = NewCommentForm(request.form)
    comment_obj = Comment.query.filter_by(id=comment_id).first()
    if current_user.username != comment_obj.owner.username:
        flash(_('You are not allowed to edit this comment'), 'error')
        return redirect(url_for('bookcloud.project', project=project))
    form.comment.default = comment_obj.content
    if request.method == 'POST':
        if form.validate():
            comment_obj.content = request.form['comment']
            db.session.commit()

            flash(_('Comment modified successfully'), 'info')
            if 'return_url' in request.args:
                return redirect(urllib.unquote(request.args['return_url']))
        else:
            form.comment.default = request.form['comment']

    threads = Thread.query.filter_by(id=comment_obj.thread_id).order_by(desc(Thread.posted_at))
    form.process()
    return render_template('newcomment.html', menu=menu, form=form, threads=threads)

@threads.route('/<project>/deletethread')
@login_required
def deletethread(project):
    thread_id = request.args['thread_id']
    if Comment.query.filter_by(thread_id=thread_id).first():
        flash(_('Thread is not empty'), 'error')
    else:
        thread = Thread.query.filter_by(id=thread_id).first()
        ownername = User.query.filter_by(id=thread.owner_id).first().username
        if not current_user.is_authenticated:
            flash(_('You must be logged in to delete a thread'), 'error')
        else:
            if current_user.username == ownername or current_user.username == get_branch_owner(project, 'master'):
                thread.user_tags = []
                #User_Tag.query.filter_by(thread_id=thread_id).delete()
                File_Tag.query.filter_by(thread_id=thread_id).delete()
                thread.custom_tags = []
                #Custom_Tag.query.filter_by(thread_id=thread_id).delete()
                Free_Tag.query.filter_by(thread_id=thread_id).delete()
                Thread.query.filter_by(id=thread_id).delete()
                db.session.commit()
                flash(_('Thread successfully deleted'), 'info')
            else:
                flash(_('You are not allowed to delete this thread'), 'error')
    return redirect(urllib.unquote(request.args['return_url']))

@threads.route('/<project>/deletecomment')
@login_required
def deletecomment(project):
    comment = Comment.get_by_id(request.args['comment_id'])
    if comment.has_replies():
        flash(_('This comment has replies and cannot be deleted'), 'error')
    else:
        if not current_user.is_authenticated:
            flash(_('You must be logged in to delete a comment'), 'error')
        else:
            ownername = User.query.filter_by(id=comment.owner_id).first().username
            if current_user.username == ownername or current_user.username == get_branch_owner(project, 'master'):
                comment.likes = []
                comment.delete()
                db.session.commit()
                flash(_('Comment successfully deleted'), 'info')
            else:
                flash(_('You are not allowed to delete this thread'), 'error')
    return redirect(urllib.unquote(request.args['return_url']))

