# Copyright 2014 SolidBuilds.com. All rights reserved
#
# Authors: Ling Thio <ling.thio@gmail.com>

from __future__ import print_function  # Use print() instead of print
from flask import url_for

import random
import string
import pytest
import shutil
import os
import re

from flask_babel import Babel, gettext as _
from application.threads import Comment

char_set = string.ascii_uppercase + string.digits

test_page = (u'Title of test page\n'
              '==================\n'
              '\n'
              'Contents:\n'
              '\n'
              '.. toctree::\n'
              '   :maxdepth: 1\n'
              '   :glob:\n'
              '\n'
              '   *\n')

def test_page_urls(client):
    # Visit home page
    response = client.get(url_for('projects.home'))
    assert _('Projects list').encode('utf8') in response.data

    # Login
    response = client.get(url_for('user.login'))
    assert b'Sign in' in response.data
    response = client.post(url_for('user.login'), follow_redirects=True,
                           data=dict(username='foo', password='Foo123'))
    assert b'You have signed in successfully' in response.data

    # Get user profile page
    response = client.get(url_for('users.profile'))
    assert (_('Your branches').encode('utf8') in response.data)

    # Update profile
    response = client.post(url_for('users.update_profile'),
                           follow_redirects=True,
                           data=dict(integer_property_01='NY'))
    assert b'NY' in response.data

    # Get page for new()
    response = client.get(url_for('projects.new'))
    assert _('Create new project') in response.data

    # Create a new project
    new_project_name = ''.join(random.sample(char_set, 20))
    response = client.post(url_for('projects.new'), follow_redirects=True,
                           data=dict(name=new_project_name))
    assert new_project_name in response.data

    # Check that project is there
    response = client.get(url_for('projects.home'))
    assert new_project_name in response.data

    # Visit new project
    response = client.get(url_for('projects.project',
                                  project=new_project_name))
    assert 'master' in response.data

    # Visit index page in master branch of project
    response = client.get(url_for('branches.view',
                                  project=new_project_name,
                                  branch='master',
                                  filename='index'))
    assert 'Welcome' in response.data

    # View edit page for index in master branch
    response = client.get(url_for('branches.edit',
                                  project=new_project_name,
                                  branch='master',
                                  filename='index'))
    assert 'math' in response.data

    # Save index page in master branch
    response = client.post(url_for('branches.edit',
                                   project=new_project_name,
                                   branch='master',
                                   filename='index'),
                           follow_redirects=True,
                           data=dict(code=test_page,
                                     html_scroll=0, edit_scroll=0))
    response = client.get(url_for('branches.view',
                              project=new_project_name,
                              branch='master',
                              filename='index'))

    assert b'Title of test page' in response.data

    # Create a new file
    response = client.post(url_for('projects.newfile',
                                   project=new_project_name,
                                   branch='master'),
                           follow_redirects=True,
                           data=dict(name='another'))
    assert _('File created successfuly!').encode('utf8') in response.data

    # Commit change
    response = client.post(url_for('branches.commit',
                                   project=new_project_name,
                                   branch='master'),
                           data=dict(message="For you!!!"))

    # Logout
    response = client.get(url_for('user.logout'), follow_redirects=True)
    assert b'You have signed out successfully.' in response.data

    # Visit index page in master branch as anonymous user
    response = client.get(url_for('branches.view',
                                  project=new_project_name,
                                  branch='master',
                                  filename='index'))
    assert 'Title of test page' in response.data
    assert 'Login' in response.data

    # Login as collaborator
    response = client.post(url_for('user.login'), follow_redirects=True,
                           data=dict(username='bar', password='Bar123'))
    assert b'You have signed in successfully' in response.data

    # Visit index page in master branch of project
    response = client.get(url_for('branches.view',
                                  project=new_project_name,
                                  branch='master',
                                  filename='index'))
    assert 'Title of test page' in response.data

    # Attempt to edit unauthorized page
    response = client.get(url_for('branches.edit',
                                  project=new_project_name,
                                  branch='master',
                                  filename='index'), follow_redirects=True)
    assert (_('You are not the owner of this branch').encode('utf8')
            in response.data)

    # Clone project
    response = client.post(url_for('branches.clone',
                                   project=new_project_name,
                                   branch='master'),
                           follow_redirects=True,
                           data=dict(name='feature'))
    assert _('Project cloned successfuly!').encode('utf8') in response.data

    # Save a change to index page in feature branch
    response = client.post(url_for('branches.edit',
                                   project=new_project_name,
                                   branch='feature',
                                   filename='index'),
                           follow_redirects=True,
                           data=dict(code=test_page + u'\nSome contents\n'
                                     + u'\u0420\u043e\u0441\u0441\u0438\u044f',
                                     html_scroll=0, edit_scroll=0))

    # Commit change
    response = client.post(url_for('branches.commit',
                                   project=new_project_name,
                                   branch='feature'), follow_redirects=True,
                           data=dict(message="For you!!!"))
    assert ((_('Page submitted to _%s') % 'master').encode('utf8')
            in response.data)

    # Log as project creator again
    response = client.get(url_for('user.logout'), follow_redirects=True)
    assert b'You have signed out successfully.' in response.data
    response = client.post(url_for('user.login'), follow_redirects=True,
                           data=dict(username='foo', password='Foo123'))
    assert b'You have signed in successfully' in response.data

    # Visit merge page
    response = client.get(url_for('branches.merge',
                                  project=new_project_name,
                                  branch='master',
                                  other='feature'))
    assert (_('Consolidando').encode('utf8') in response.data
            or _('Merging').encode('utf8') in response.data)

    # Accepting suggestions
    response = client.get(url_for('branches.accept',
                                  project=new_project_name,
                                  branch='master',
                                  filename='index.rst'), follow_redirects=True)
    assert (_('You have finished all the reviews').encode('utf8')
            in response.data)

    # Finishing merge
    response = client.get(url_for('branches.finish',
                                  project=new_project_name,
                                  branch='master'), follow_redirects=True)
    assert ((_('You have finished merging _%s') % 'feature').encode('utf8')
            in response.data)

    # Check changes took place
    response = client.get(url_for('branches.view',
                                  project=new_project_name,
                                  branch='master',
                                  filename='index'))
    assert 'Some contents' in response.data

    # Logout
    response = client.get(url_for('user.logout'), follow_redirects=True)
    assert b'You have signed out successfully.' in response.data

    # Login as second order collaborator
    response = client.post(url_for('user.login'), follow_redirects=True,
                           data=dict(username='bla', password='Bla123'))
    assert b'You have signed in successfully' in response.data

    # Clone the feature branch
    response = client.post(url_for('branches.clone',
                                   project=new_project_name,
                                   branch='feature'),
                           follow_redirects=True,
                           data=dict(name='typo'))
    assert _('Project cloned successfuly!').encode('utf8') in response.data

    # Create a new file
    response = client.post(url_for('projects.newfile',
                                   project=new_project_name,
                                   branch='typo'),
                           follow_redirects=True,
                           data=dict(name='another'))
    assert _('You are not the owner of master').encode('utf8') in response.data

    # Commit change
    response = client.post(url_for('branches.commit',
                                   project=new_project_name,
                                   branch='typo'), follow_redirects=True,
                           data=dict(message="For you!!!"))
    assert ((_('Page submitted to _%s') % 'feature').encode('utf8')
            in response.data)

    # Log as project creator again
    response = client.get(url_for('user.logout'), follow_redirects=True)
    assert b'You have signed out successfully.' in response.data
    response = client.post(url_for('user.login'), follow_redirects=True,
                           data=dict(username='foo', password='Foo123'))
    assert b'You have signed in successfully' in response.data

    # Visit main page (don't see merge request)
    response = client.get(url_for('branches.view',
                                  project=new_project_name,
                                  branch='master',
                                  filename='index.html'))
    assert 'Title of test page' in response.data

    # Log as project first order contributor
    response = client.get(url_for('user.logout'), follow_redirects=True)
    assert b'You have signed out successfully.' in response.data
    response = client.post(url_for('user.login'), follow_redirects=True,
                           data=dict(username='bar', password='Bar123'))
    assert b'You have signed in successfully' in response.data

    # Merging from typo to feature
    response = client.get(url_for('branches.merge',
                                  project=new_project_name,
                                  branch='feature',
                                  other='typo'))
    assert ('Consolidando' in response.data
            or 'Merging' in response.data)
    response = client.get(url_for('branches.accept',
                                  project=new_project_name,
                                  branch='feature',
                                  filename='another.rst'),
                          follow_redirects=True)
    assert (_('You have finished all the reviews').encode('utf8')
            in response.data)
    response = client.get(url_for('branches.finish',
                                  project=new_project_name,
                                  branch='feature'), follow_redirects=True)
    assert ((_('You have finished merging _%s') % 'typo').encode('utf8')
            in response.data)
    response = client.get(url_for('branches.view',
                                  project=new_project_name,
                                  branch='feature',
                                  filename='another'))
    assert '<h1>another' in response.data

    # Log as project creator again
    response = client.get(url_for('user.logout'), follow_redirects=True)
    assert b'You have signed out successfully.' in response.data
    response = client.post(url_for('user.login'), follow_redirects=True,
                           data=dict(username='foo', password='Foo123'))
    assert b'You have signed in successfully' in response.data

    # Merging from feature to master
    response = client.get(url_for('branches.merge',
                                  project=new_project_name,
                                  branch='master',
                                  other='feature'))
    assert ('Consolidando' in response.data or 'Merging' in response.data)
    response = client.get(url_for('branches.accept',
                                  project=new_project_name,
                                  branch='master',
                                  filename='another.rst'),
                          follow_redirects=True)

    assert (_('You have finished all the reviews').encode('utf8')
            in response.data)
    response = client.get(url_for('branches.finish',
                                  project=new_project_name,
                                  branch='master'), follow_redirects=True)
    assert ((_('You have finished merging _%s') % 'feature').encode('utf8')
            in response.data)
    response = client.get(url_for('branches.view',
                                  project=new_project_name,
                                  branch='master',
                                  filename='another'))
    assert '<h1>another' in response.data

    # Testing comments
    # GET newthread
    response = client.get(url_for('threads.newthread',
                                  project=new_project_name))
    assert 'foo' in response.data
    assert 'index' in response.data

    # POST newthread
    response = client.post(url_for('threads.newthread',
                                   project=new_project_name),
                           follow_redirects=True,
                           data=dict(title="Hi there!",
                                     flag="discussion",
                                     firstcomment="Give me some attention!",
                                     usertags='["foo"]',
                                     filetags='[]',
                                     namedtags='[]',
                                     freetags='["last", "one"]'))
    assert (("criado com sucesso" in response.data)
            or ("successfully created" in response.data))

    # View thread in project page
    response = client.get(url_for('projects.project',
                              project=new_project_name))
    match = re.search(r'new_comment/(\d+)/000000:', response.data)
    thread_id = match.group(1)
    comment = (Comment.query
               .filter(Comment.content.like('%attention%'))
               .first())
    assert "Give me some attention!" in response.data

    # POST reply
    response = client.post(url_for('threads.newcomment',
                                   project=new_project_name,
                                   thread_id=thread_id,
                                   parent_lineage="000000:"),
                           follow_redirects=True,
                           data=dict(comment="Please!"))
    reply = (Comment.query
             .filter(Comment.content.like('%Please!%'))
             .first())
    assert (("criado com sucesso" in response.data)
            or ("successfully created" in response.data))

    # Check reply
    response = client.get(url_for('projects.project',
                              project=new_project_name))
    assert "Please!" in response.data

    # Try to delete thread
    response = client.get(url_for('threads.deletethread',
                                  project=new_project_name,
                                  thread_id=thread_id),
                          follow_redirects=True,
                          data=dict(return_url=url_for('projects.home',
                                                       _external=True)))
    assert "vazio" in response.data

    # Try to delete comment
    response = client.get(url_for('threads.deletecomment',
                                  project=new_project_name,
                                  comment_id=comment.id),
                          follow_redirects=True,
                          data=dict(return_url=url_for('projects.home',
                                                       _external=True)))
    assert (_('This comment has replies and cannot be deleted').encode('utf8')
            in response.data)

    # Delete reply
    response = client.get(url_for('threads.deletecomment',
                                  project=new_project_name,
                                  comment_id=reply.id),
                          follow_redirects=True,
                          data=dict(return_url=url_for('projects.home',
                                                       _external=True)))
    assert (_('Comment successfully deleted').encode('utf8')
            in response.data)

    # Delete first comment
    response = client.get(url_for('threads.deletecomment',
                                  project=new_project_name,
                                  comment_id=comment.id),
                          follow_redirects=True,
                          data=dict(return_url=url_for('projects.home',
                                                       _external=True)))
    assert (_('Comment successfully deleted').encode('utf8')
            in response.data)

    # Delete thread
    response = client.get(url_for('threads.deletethread',
                                  project=new_project_name,
                                  thread_id=thread_id),
                          follow_redirects=True,
                          data=dict(return_url=url_for('projects.home',
                                                       _external=True)))
    assert (_('Thread successfully deleted').encode('utf8')
            in response.data)

    shutil.rmtree(os.path.abspath(os.path.join('repos', new_project_name)))







