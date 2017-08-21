import urllib
import json
from sets import Set
from datetime import datetime
from os.path import join

from flask import (
    Blueprint, request, render_template,
    url_for, flash, redirect, g, abort
)
from flask_user import login_required, current_user
from flask_babel import gettext as _
from flask_mail import Message
from sqlalchemy import or_, not_, desc

import application
from application import db, app, limiter, mail
from application.users import User
from application.utils import rst2html
from application.threads import (
    Thread, Comment, File_Tag, Free_Tag, Named_Tag, CommentSearchForm,
    ThreadForm, NewThreadForm, CommentForm, ThreadQueryForm, user_read_thread
)
from application.projects import Project

threads = Blueprint('threads', __name__)

@threads.url_value_preprocessor
def get_branch_object(endpoint, values):
    g.project = Project.get_by_name(values.get('project'))
    values['project'] = g.project

@threads.before_request
def threads_before_request():
    application.views.projects.projects_before_request()

@threads.context_processor
def threads_context_processor():
    return { 'project': g.project,
             'menu': g.menu }

@threads.route('/<project>/new_thread', methods = ['GET', 'POST'])
@login_required
def newthread(project):
    inputs = {'user_tags': '', 'file_tags': '',
              'custom_tags': '', 'free_tags': ''}
    for t in inputs:
        inputs[t] = request.args.get(t) if request.args.get(t) else ''
    # In the next line we are deleting some inputs if they
    # were inserted but not validated in a previous new_thread view
    form = NewThreadForm(request.form,
                         user_tags=inputs['user_tags'].split(","),
                         file_tags=inputs['file_tags'].split(","),
                         custom_tags=inputs['custom_tags'].split(","),
                         free_tags=inputs['free_tags'])
    form.user_tags.widget.choices = json.dumps(
        [u.username for u in User.query.all()])
    form.file_tags.widget.choices = project.get_labels()
    form.custom_tags.widget.choices = json.dumps(
        [t.name for t in Named_Tag.query.filter_by(project=project).all()])
    if request.method == 'POST' and form.validate():
        # create thread
        new_thread = Thread(form.title.data,
                            current_user.id,
                            project.id,
                            form.flag.data,
                            datetime.utcnow())
        # add tags
        new_thread.user_tags = [User.get_by_name(n)
                                for n in form.user_tags.data]
        new_thread.file_tags = [File_Tag(new_thread.id, n)
                                for n in form.file_tags.data]
        new_thread.custom_tags = list(
            Named_Tag.query.filter(Named_Tag.project==project,
                                   Named_Tag.name.in_(form.custom_tags.data))
                           .all())
        new_thread.free_tags = [Free_Tag(new_thread.id, n)
                                for n in form.free_tags.data]
        # add first comment
        new_comment = Comment('000000:',
                              new_thread.id,
                              current_user.id,
                              form.firstcomment.data,
                              datetime.utcnow())
        new_thread.comments = [new_comment]
        db.session.add(new_thread)
        db.session.commit()
        # send emails
        message = render_template('threads/email.html', comment=new_comment)
        recipients = Set(form.user_tags.data)
        for tags in new_thread.custom_tags:
            recipients = recipients | Set([u.username for u in
                                           tags.subscribed_users])
        if app.config['TESTING']:
            print('Email should be sent to: ' + str(recipients))
            print(message)
        else:
            with mail.connect() as conn:
                for user in recipients:
                    user_obj = User.get_by_name(user)
                    subject = _('Thread: ') + new_thread.title
                    msg = Message(recipients=[user_obj.email],
                                  subject=subject,
                                  html=message)
                    conn.send(msg)
                flash(_('Emails sent to user(s) {}')
                      .format(str(recipients)))
        flash(_('New thread successfully created'), 'info')
        if 'return_url' in request.args:
            redirect(urllib.unquote(request.args['return_url']))
        else:
            return redirect(url_for('branches.view', project=project.name,
                                    branch='master', filename='index'))
    return render_template('threads/newthread.html', form=form)

@threads.route('/<project>/edit_thread/<thread_id>', methods = ['GET', 'POST'])
@login_required
def editthread(project, thread_id):
    thread = Thread.get_by_id(thread_id)
    if (current_user != thread.owner):
        flash(_('You are not allowed to edit this thread'), 'error')
        return redirect(url_for('branches.view', project=project.name,
                                branch='master', filename='index'))
    form = ThreadForm(
        request.form,
        title=thread.title,
        flag=thread.flag,
        user_tags=[t.username for t in thread.user_tags],
        file_tags=[t.filename for t in thread.file_tags],
        custom_tags=[t.name for t in thread.custom_tags],
        free_tags=[t.name for t in thread.free_tags])
    form.user_tags.widget.choices = json.dumps(
        [u.username for u in User.query.all()])
    form.file_tags.widget.choices = project.get_labels()
    form.custom_tags.widget.choices = json.dumps(
        [t.name for t
         in Named_Tag.query.filter_by(project=project).all()])
    master_path = join('repos', project.name, 'master', 'source')
    if request.method == 'POST' and form.validate():
        thread.title = form.title.data
        thread.flag = form.flag.data
        # add tags
        thread.user_tags = [User.get_by_name(n)
                            for n in form.user_tags.data]
        thread.file_tags = [File_Tag(thread.id, n)
                            for n in form.file_tags.data]
        thread.custom_tags = list(
            Named_Tag.query.filter(Named_Tag.project==project,
                                   Named_Tag.name.in_(form.custom_tags.data))
                           .all())
        thread.free_tags = [Free_Tag(thread.id, n)
                            for n in form.free_tags.data]
        db.session.commit()
        flash(_('Thread successfully modified'), 'info')
        if 'return_url' in request.args:
            return redirect(urllib.unquote(request.args['return_url']))
        else:
            return redirect(url_for('branches.view', project=project.name,
                                    branch='master', filename='index'))
    return render_template('threads/editthread.html', form=form)

@threads.route('/<project>/delete_thread/<int:thread_id>')
@login_required
def deletethread(project, thread_id):
    thread = Thread.get_by_id(thread_id)
    if Comment.query.filter_by(thread_id=thread_id).first():
        flash(_('Thread is not empty'), 'error')
    else:
        thread = Thread.query.filter_by(id=thread_id).first()
        if not current_user.is_authenticated:
            flash(_('You must be logged in to delete a thread'), 'error')
        else:
            if (current_user != thread.owner
                and current_user != project.get_master().owner):
                flash(_('You are not allowed to delete this thread'), 'error')
            else:
                thread.delete()
                db.session.commit()
                flash(_('Thread successfully deleted'), 'info')
    if 'return_url' in request.args:
        return redirect(urllib.unquote(request.args['return_url']))
    else:
        return redirect(url_for('branches.view', project=project.name,
                                branch='master', filename='index'))

@threads.route('/<project>/new_comment/<thread_id>', methods = ['GET', 'POST'])
@threads.route('/<project>/new_comment/<thread_id>/<parent_lineage>',
               methods = ['GET', 'POST'])
@login_required
def newcomment(project, thread_id, parent_lineage=''):
    form = CommentForm(request.form)
    if (parent_lineage != ''):
        try:
           (Comment.query.filter(Comment.thread_id==thread_id)
            .filter(Comment.lineage==parent_lineage).one())
        except:
            abort(404)
    if request.method == 'POST' and form.validate():
        thread = Thread.get_by_id(thread_id)
        siblings_pattern = parent_lineage + '%'
        decend_comments = (Comment.query
                           .filter(Comment.thread_id==thread_id)
                           .filter(Comment.lineage.like(siblings_pattern)))
        number_siblings = decend_comments.count()
        new_comment_lineage = (parent_lineage
                               + format(number_siblings, '06X') + ':')
        new_comment = Comment(new_comment_lineage,
                              thread_id,
                              current_user.id,
                              form.comment.data,
                              datetime.utcnow())
        db.session.add(new_comment)
        db.session.commit()
        # send emails
        recipients = Set([tag.username for tag in thread.user_tags])
        for tags in thread.custom_tags:
            recipients = recipients | Set([u.username for u in
                                           tags.subscribed_users])
        message = render_template('threads/email.html', comment=new_comment)
        if app.config['TESTING']:
            print('Email should be sent to: ' + str(recipients))
            print(message)
        else:
            with mail.connect() as conn:
                for user in recipients:
                    user_obj = User.query.filter_by(username=user).first()
                    subject = _('Thread: ') + thread.title
                    msg = Message(recipients=[user_obj.email],
                                  html=message,
                                  subject=subject)
                    conn.send(msg)
                flash(_('Emails sent to user(s) {}')
                      .format(str(recipients)))
        flash(_('New comment successfully created'), 'info')
        if 'return_url' in request.args:
            return redirect(urllib.unquote(request.args['return_url']))
    label_file_dict = project.get_label_file_dict()
    return render_template('threads/newcomment.html', form=form,
                           label_file_dict=label_file_dict)

@threads.route('/<project>/edit_comment/<comment_id>',
               methods = ['GET', 'POST'])
@login_required
def editcomment(project, comment_id):
    comment = Comment.get_by_id(comment_id)
    form = CommentForm(request.form,
                       comment=comment.content)
    if current_user != comment.owner:
        flash(_('You are not allowed to edit this comment'), 'error')
        if 'return_url' in request.args:
            return redirect(urllib.unquote(request.args['return_url']))
        else:
            return redirect(url_for('branches.view', project=project.name,
                                    branch='master', filename='index'))
    if request.method == 'POST' and form.validate():
            comment.content = form.comment.data
            db.session.commit()
            flash(_('Comment modified successfully'), 'info')
            if 'return_url' in request.args:
                return redirect(urllib.unquote(request.args['return_url']))
            else:
                return redirect(url_for('branches.view', project=project.name,
                                        branch='master', filename='index'))
    threads = (Thread.query.filter_by(id=comment.thread.id)
               .order_by(desc(Thread.posted_at)))
    return render_template('threads/newcomment.html', form=form)

@threads.route('/<project>/delete_comment/<int:comment_id>')
@login_required
def deletecomment(project, comment_id):
    comment = Comment.get_by_id(comment_id)
    if comment.has_replies():
        flash(_('This comment has replies and cannot be deleted'), 'error')
    else:
        if not current_user.is_authenticated:
            flash(_('You must be logged in to delete a comment'), 'error')
        else:
            if (current_user != comment.owner
                and current_user != project.get_master().owner):
                flash(_('You are not allowed '
                        'to delete this thread'), 'error')
            else:
                comment.delete()
                db.session.commit()
                flash(_('Comment successfully deleted'), 'info')
    if 'return_url' in request.args:
        return redirect(urllib.unquote(request.args['return_url']))
    else:
        return redirect(url_for('branches.view', project=project.name,
                                branch='master', filename='index'))

@threads.route('/<project>/query_thread', methods = ['GET'])
def query_thread(project):
    form = ThreadQueryForm(request.args)
    form.user_tags.widget.choices = json.dumps(
        [u.username for u in User.query.all()])
    form.file_tags.widget.choices = project.get_labels()
    form.custom_tags.widget.choices = json.dumps(
        [t.name for t in Named_Tag.query.filter_by(project=project).all()])
    if form.validate():
        threads = (Thread.query.filter(Thread.project==project)
                   .join(Comment))
        if request.args.get('search'):
            threads = threads.filter(or_(
                Comment.content.like('%' + request.args.get('search') + '%'),
                Thread.title.like('%' + request.args.get('search') + '%')))
        if request.args.get('thread_id'):
            threads = threads.filter(Thread.id==request.args.get('thread_id'))
        if (request.args.get('unread') and request.args.get('unread') == 'y'):
            threads = (threads.filter(
                not_(Thread.user_read_thread.any(id=current_user.id))))
        if request.args.get('user_tags'):
            try:
                user_list = json.loads(request.args.get('user_tags'))
            except:
                abort(404)
            if len(user_list):
                user_list_id = [User.get_by_name(n).id for n in user_list]
                threads = threads.filter(or_(
                    Thread.owner_id.in_(user_list_id),
                    Comment.owner_id.in_(user_list_id)))
        if request.args.get('file_tags'):
            try:
                file_list = json.loads(request.args.get('file_tags'))
            except:
                abort(404)
            if len(file_list):
                threads = threads.join(File_Tag).filter(
                    File_Tag.filename.in_(file_list))
        if request.args.get('custom_tags'):
            try:
                custom_tag_list = json.loads(request.args.get('custom_tags'))
            except:
                abort(404)
            if len(custom_tag_list):
                threads = threads.join(Named_Tag, Thread.custom_tags).filter(
                    Named_Tag.name.in_(custom_tag_list))
        threads = threads.order_by(desc(Thread.posted_at)).limit(100)
    else:
        threads = (Thread.query
                   .filter_by(project=project)
                   .order_by(desc(Thread.posted_at))
                   .limit(100))
    label_file_dict = project.get_label_file_dict()
    return render_template('threads/query_threads.html', threads=threads,
                           form=form, label_file_dict=label_file_dict)

# API routes
@threads.route('/<project>/preview_comment', methods = ['GET', 'POST'])
def preview_comment(project):
    input = ''
    if request.method == 'POST':
        if request.form.has_key('content'):
            input = rst2html(request.form.get('content'))
    return input

@threads.route('/<project>/<comment_id>/like', methods = ['POST'])
def like_comment(project, comment_id):
    if not current_user.is_authenticated:
        return json.dumps({
            'message': _('You must be logged in to like a comment'),
            'status': 'error'
            })
    comment = Comment.get_by_id(comment_id)
    if current_user == comment.owner:
        return json.dumps({
            'message': _('You cannot like/unlike your own comment'),
            'status': 'error'
            })
    if request.form.get('is_like') == 'true':
        if current_user in comment.likes:
            return json.dumps({
                'message': _('You have already liked this comment'),
                'status': 'error'
                })
        comment.likes.append(current_user)
        db.session.commit()
        return json.dumps({
            'message': _('Like registered!'),
            'number_of_likes': comment.likes.count(),
            'status': 'success'})
    else:
        if not current_user in comment.likes:
            return json.dumps({
                'message': _('You have not liked this comment'),
                'status': 'error'
                })
        comment.likes.remove(current_user)
        db.session.commit()
        return json.dumps({
            'message': _('Like removed!'),
            'number_of_likes': comment.likes.count(),
            'status': 'success'})

@threads.route('/<project>/<thread_id>/mark_read', methods = ['POST'])
def mark_read(project, thread_id):
    if not current_user.is_authenticated:
        return json.dumps({
            'message': _('You must be logged in to mark a comment read'),
            'status': 'error'
            })
    thread = Thread.get_by_id(thread_id)
    if request.form.get('is_read') == 'true':
        if current_user in thread.user_read_thread:
            return json.dumps({
                'message': _('You have already read this thread'),
                'status': 'error'
                })
        thread.user_read_thread.append(current_user)
        db.session.commit()
        return json.dumps({
            'message': _('Marked as read!'),
            'status': 'success'})
    else:
        if not current_user in thread.user_read_thread:
            return json.dumps({
                'message': _('You have not read this thread'),
                'status': 'error'
                })
        thread.user_read_thread.remove(current_user)
        db.session.commit()
        return json.dumps({
            'message': _('Marked as unread!'),
            'status': 'success'})




