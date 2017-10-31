import os.path
import time
import locale

from dulwich.objects import Blob
from flask import redirect, url_for, flash

from flask_babel import gettext as _

from diff import render_diff

class Custom404(Exception):
    def __init__(self,*args,**kwargs):
        Exception.__init__(self,*args,**kwargs)

def window(iterable):
    # Turns an iterable into a moving window
    # [0, ..., 10] -> [(None, 0, 1), (0, 1, 2), ..., (8, 9, None), (9, None, None)]
    iterator = iter(iterable)
    prev_item = None
    current_item = next(iterator)  # throws StopIteration if empty.
    for next_item in iterator:
        yield (prev_item, current_item, next_item)
        prev_item = current_item
        current_item = next_item
    yield (prev_item, current_item, None)

from flask_user import current_user
from flask_limiter.util import get_remote_address

def get_identifier():
    if current_user.is_authenticated:
        return current_user.username
    return get_remote_address()

# for rst2html
from docutils.core import publish_string, publish_parts
from docutils_tinyhtml import Writer

def rst2html(input):
    def convertion_attempt(rst):
        writer = Writer()
        # store full html output to html variable
        html = publish_string(source=rst,
                              writer=writer,
                              writer_name='html',
                              settings_overrides={'math-output': 'html',
                                                  'link': 'link',
                                                  'top': 'top'})
        # disable system message in html, no in stderr
        parts = publish_parts(source=rst,
                              writer=writer,
                              writer_name='html',
                              settings_overrides={'no_system_messages': True})
        # store only html body
        body = parts['html_title'] + parts['body'] + parts['html_line'] + \
            parts['html_footnotes'] + parts['html_citations'] + \
            parts['html_hyperlinks']
        return body
    try:
        return convertion_attempt(input)
    except:
        return ('<b>' + _('Error in compiling comment') + '</b><br />'
                   + input.replace("\n","<br />\n"))

def force_unicode(s):
    """Do all kinds of magic to turn `s` into unicode"""
    # It's already unicode, don't do anything:
    #if isinstance(s, six.text_type):
    #    return s
    # Try some default encodings:
    try:
        return s.decode('utf-8')
    except UnicodeDecodeError as exc:
        pass
    try:
        return s.decode(locale.getpreferredencoding())
    except UnicodeDecodeError:
        pass
    if chardet is not None:
        # Try chardet, if available
        encoding = chardet.detect(s)['encoding']
        if encoding is not None:
            return s.decode(encoding)
    raise # Give up.

def extract_author_name(email):
    """Extract the name from an email address --
    >>> extract_author_name("John <john@example.com>")
    "John"
    -- or return the address if none is given.
    >>> extract_author_name("noname@example.com")
    "noname@example.com"
    """
    match = re.match('^(.*?)<.*?>$', email)
    if match:
        return match.group(1).strip()
    return email

def formattimestamp(timestamp):
    return (datetime.fromtimestamp(timestamp)
            .strftime('%b %d, %Y %H:%M:%S'))

def timesince(when, now=time.time):
    """Return the difference between `when` and `now` in human
    readable form."""
    #return naturaltime(now() - when)
    return (now() - when)

# for timeouts
import subprocess, threading

# to run a process with timeout
class Command(object):
    def __init__(self, cmd):
        self.cmd = cmd
        self.process = None

    def run(self, timeout):
        def target():
            self.process = subprocess.Popen(self.cmd, shell=True)
            self.process.communicate()

        thread = threading.Thread(target=target)
        thread.start()

        thread.join(timeout)
        if thread.is_alive():
            flash(_('Process is taking too long and will be terminated!'),
                  'error')
            self.process.terminate()
            thread.join()

# git related tools
import git
import string
from os.path import isfile, join
import codecs # deals with encoding better
import json

def load_file(path):
    with codecs.open(path, 'r', 'utf-8') as content_file:
        return content_file.read()

def write_file(path, contents):
    UTF8Writer = codecs.getwriter('utf8')
    with open(path, 'w') as dest_file:
        dest_file.write(contents.encode('utf8'))

import subprocess
import arrow
import os

def last_modified(project, branch):
    branch_source_path = os.path.abspath(join('repos', project, branch, 'source'))
    command = 'find ' + branch_source_path + ' -printf "%TY-%Tm-%Td %TT\n" | sort -nr | head -n 1'
    timestamp = arrow.get(subprocess.check_output(command, shell=True))
    return(timestamp.humanize())

from wtforms.widgets import html_params
from wtforms import (
    StringField, validators
)

def create_message(name):
    return StringField(name, [
        validators.Length(min=4, max=60),
        validators.Regexp('^[\w ,.?!-]+$',
                          message="Messages must contain only a-zA-Z0-9_-,.!? and space")])

def create_message_special(name):
    return StringField(name, [
        validators.Length(min=4, max=60),
        validators.Regexp(
            '^[\xe3\xf5\xe2\xea\xf4\xe1\xe9\xed\xf3\xfa\xfc\xe0\xe7\xc3\xd5'
            '\xc2\xca\xd4\xc1\xc9\xcd\xd3\xda\xdc\xc0\xc7\w ,.?!-]+$',
            message='Messages must contain only a-zA-Z0-9_-,.!?'
            'and space')])

def create_identifier(name):
    return StringField(name, [
        validators.Length(min=4, max=25),
        validators.Regexp(
            '^[a-zA-Z0-9][\w-]+$',
            message=_('Identifiers must contain only a-zA-Z0-9_- '
                      'and cannot start with - or _'))])

def select_multi_checkbox(field, ul_class='', **kwargs):
    kwargs.setdefault('type', 'checkbox')
    field_id = kwargs.pop('id', field.id)
    html = [u'<ul style="list-style-type: none; padding-left: 0px;" %s>' % html_params(id=field_id, class_=ul_class)]
    for value, label, checked in field.iter_choices():
        choice_id = u'%s-%s' % (field_id, value)
        options = dict(kwargs, name=field.name, value=value, id=choice_id)
        if checked:
            options['checked'] = 'checked'
        html.append(u'<li><input style="margin-left: 0px;" %s /> ' % html_params(**options))
        html.append(u'<label for="%s">%s</label></li>' % (field_id, label))
    html.append(u'</ul>')
    return u''.join(html)


def commit_diff(repo, old_commit, new_commit):
    """Return the list of changes introduced from old to new commit."""
    summary = {'nfiles': 0, 'nadditions':  0, 'ndeletions':  0}
    file_changes = []  # the changes in detail
    dulwich_changes = repo.object_store.tree_changes(old_commit.tree,
                                                     new_commit.tree)
    for (oldpath, newpath), (oldmode, newmode), (oldsha, newsha) \
        in dulwich_changes:
        summary['nfiles'] += 1
        try:
            oldblob = (repo.object_store[oldsha] if oldsha
                       else Blob.from_string(b''))
            newblob = (repo.object_store[newsha] if newsha
                       else Blob.from_string(b''))
        except KeyError:
            # newsha/oldsha are probably related to submodules.
            # Dulwich will handle that.
            pass
        additions, deletions, chunks = render_diff(
            oldblob.splitlines(), newblob.splitlines())
        change = {
            'is_binary': False,
            'old_filename': oldpath or '/dev/null',
            'new_filename': newpath or '/dev/null',
            'chunks': chunks,
            'additions': additions,
            'deletions': deletions,
        }
        summary['nadditions'] += additions
        summary['ndeletions'] += deletions
        file_changes.append(change)
    return summary, file_changes

def extension(filename):
    ext = os.path.splitext(filename)[1]
    if ext.startswith('.'):
        # os.path.splitext retains . separator
        ext = ext[1:]
    return ext

def lowercase_ext(filename):
    """
    This is a helper used by UploadSet.save to provide lowercase extensions for
    all processed files, to compare with configured extensions in the same
    case.
    :param filename: The filename to ensure has a lowercase extension.
    """
    if '.' in filename:
        main, ext = os.path.splitext(filename)
        return main + ext.lower()
    # For consistency with os.path.splitext,
    # do not treat a filename without an extension as an extension.
    # That is, do not return filename.lower().
    return filename

def resolve_conflict(target_folder, basename):
        """
        If a file with the selected name already exists in the target folder,
        this method is called to resolve the conflict. It should return a new
        basename for the file.
        The default implementation splits the name and extension and adds a
        suffix to the name consisting of an underscore and a number, and tries
        that until it finds one that doesn't exist.
        :param target_folder: The absolute path to the target.
        :param basename: The file's original basename.
        """
        name, ext = os.path.splitext(basename)
        count = 0
        while True:
            count = count + 1
            newname = '%s_%d%s' % (name, count, ext)
            if not os.path.exists(os.path.join(target_folder, newname)):
                return newname


