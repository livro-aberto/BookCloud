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

char_set = string.ascii_uppercase + string.digits

def test_page_urls(client):
    # Visit home page
    response = client.get(url_for('bookcloud.projects'))
    assert b'Projects list' in response.data

    # Login
    response = client.get(url_for('user.login'))
    assert b'Sign in' in response.data
    response = client.post(url_for('user.login'), follow_redirects=True,
                           data=dict(username='foo', password='Foo123'))
    assert b'You have signed in successfully' in response.data

    # Get user profile page
    response = client.get(url_for('bookcloud.profile'))
    assert b'Hi foo' in response.data

    # Get page for new()
    response = client.get(url_for('bookcloud.new'))
    assert b'Create new project' in response.data

    # Create a new project
    new_project_name = ''.join(random.sample(char_set, 20))
    response = client.post(url_for('bookcloud.new'), follow_redirects=True,
                           data=dict(project=new_project_name))
    assert new_project_name in response.data

    # Check that project is there
    response = client.get(url_for('bookcloud.projects'))
    assert new_project_name in response.data

    # Visit new project
    response = client.get(url_for('bookcloud.branches',
                                  project=new_project_name))
    assert 'master' in response.data

    # Visit index page in master branch of project
    response = client.get(url_for('bookcloud.view',
                                  project=new_project_name,
                                  branch='master',
                                  filename='index'))
    assert 'Welcome' in response.data

    # View edit page for index in master branch
    response = client.get(url_for('bookcloud.edit',
                                  project=new_project_name,
                                  branch='master',
                                  filename='index'))
    assert 'Math mode' in response.data

    # Save index page in master branch
    response = client.post(url_for('bookcloud.save',
                                   project=new_project_name,
                                   branch='master',
                                   filename='index'),
                           follow_redirects=True,
                           data=dict(code='Title of test page\n=================='))
    assert b'Title of test page' in response.data

    # Logout
    response = client.get(url_for('user.logout'), follow_redirects=True)
    assert b'You have signed out successfully.' in response.data

    # Visit index page in master branch as anonymous user
    response = client.get(url_for('bookcloud.view',
                                  project=new_project_name,
                                  branch='master',
                                  filename='index'))
    assert 'Title of test page' in response.data
    assert 'login' in response.data

    # Login as collaborator
    response = client.post(url_for('user.login'), follow_redirects=True,
                           data=dict(username='bar', password='Bar123'))
    assert b'You have signed in successfully' in response.data

    # Visit index page in master branch of project
    response = client.get(url_for('bookcloud.view',
                                  project=new_project_name,
                                  branch='master',
                                  filename='index'))
    assert 'Title of test page' in response.data

    # Attempt to edit unauthorized page
    response = client.get(url_for('bookcloud.edit',
                                  project=new_project_name,
                                  branch='master',
                                  filename='index'), follow_redirects=True)
    assert 'You are not the owner of this branch' in response.data

    # Clone project
    response = client.post(url_for('bookcloud.clone',
                                   project=new_project_name,
                                   branch='master'),
                           follow_redirects=True,
                           data=dict(name='feature'))
    assert b'Project cloned successfuly!' in response.data

    # Save a change to index page in feature branch
    response = client.post(url_for('bookcloud.save',
                                   project=new_project_name,
                                   branch='feature',
                                   filename='index'),
                           follow_redirects=True,
                           data=dict(code='Title of test page\n==================\n\nSome contents...'))
    assert b'Page submitted to _master' in response.data

    # Log as project creator again
    response = client.get(url_for('user.logout'), follow_redirects=True)
    assert b'You have signed out successfully.' in response.data
    response = client.post(url_for('user.login'), follow_redirects=True,
                           data=dict(username='foo', password='Foo123'))
    assert b'You have signed in successfully' in response.data

    # Visit merge page
    response = client.get(url_for('bookcloud.merge',
                                  project=new_project_name,
                                  branch='master',
                                  other='feature'))
    assert 'Merging from _feature' in response.data

    # Accepting suggestions
    response = client.get(url_for('bookcloud.accept',
                                  project=new_project_name,
                                  branch='master',
                                  filename='index.rst'), follow_redirects=True)
    assert 'You have finished all the reviews' in response.data

    # Finishing merge
    response = client.get(url_for('bookcloud.finish',
                                  project=new_project_name,
                                  branch='master'), follow_redirects=True)
    assert 'You have finished merging _feature' in response.data
    assert 'Some contents' in response.data


    # Logout
    response = client.get(url_for('user.logout'), follow_redirects=True)
    assert b'You have signed out successfully.' in response.data

    # Login as second order collaborator
    response = client.post(url_for('user.login'), follow_redirects=True,
                           data=dict(username='bla', password='Bla123'))
    assert b'You have signed in successfully' in response.data

    # Clone the feature branch
    response = client.post(url_for('bookcloud.clone',
                                   project=new_project_name,
                                   branch='feature'),
                           follow_redirects=True,
                           data=dict(name='typo'))
    assert b'Project cloned successfuly!' in response.data

    # Save a change in typo branch
    response = client.post(url_for('bookcloud.save',
                                   project=new_project_name,
                                   branch='typo',
                                   filename='index'),
                           follow_redirects=True,
                           data=dict(code='Title of test page\n==================\n\nSome more contents...'))
    assert b'Page submitted to _feature' in response.data

    # Log as project creator again
    response = client.get(url_for('user.logout'), follow_redirects=True)
    assert b'You have signed out successfully.' in response.data
    response = client.post(url_for('user.login'), follow_redirects=True,
                           data=dict(username='foo', password='Foo123'))
    assert b'You have signed in successfully' in response.data

    # Visit main page (don't see merge request)
    response = client.get(url_for('bookcloud.view',
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

    # Visit feature branch to see the request
    response = client.get(url_for('bookcloud.view',
                                  project=new_project_name,
                                  branch='feature',
                                  filename='index.html'))
    assert 'Request from' in response.data

    # Merging from typo to feature
    response = client.get(url_for('bookcloud.merge',
                                  project=new_project_name,
                                  branch='feature',
                                  other='typo'))
    assert 'Merging from _feature' in response.data
    response = client.get(url_for('bookcloud.accept',
                                  project=new_project_name,
                                  branch='feature',
                                  filename='index.rst'), follow_redirects=True)
    assert 'You have finished all the reviews' in response.data
    response = client.get(url_for('bookcloud.finish',
                                  project=new_project_name,
                                  branch='feature'), follow_redirects=True)
    assert 'You have finished merging _typo' in response.data
    assert 'Some more contents' in response.data

    # Log as project creator again
    response = client.get(url_for('user.logout'), follow_redirects=True)
    assert b'You have signed out successfully.' in response.data
    response = client.post(url_for('user.login'), follow_redirects=True,
                           data=dict(username='foo', password='Foo123'))
    assert b'You have signed in successfully' in response.data

    # Merging from feature to master
    response = client.get(url_for('bookcloud.merge',
                                  project=new_project_name,
                                  branch='master',
                                  other='feature'))
    assert 'Merging from _feature' in response.data
    response = client.get(url_for('bookcloud.accept',
                                  project=new_project_name,
                                  branch='master',
                                  filename='index.rst'), follow_redirects=True)

    assert 'You have finished all the reviews' in response.data
    response = client.get(url_for('bookcloud.finish',
                                  project=new_project_name,
                                  branch='master'), follow_redirects=True)
    assert 'You have finished merging _feature' in response.data
    assert 'Some more contents' in response.data





    shutil.rmtree(os.path.abspath(os.path.join('repos', new_project_name)))
