from flask import redirect, url_for, flash

from flask_babel import gettext as _

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


# for rst2html
from docutils.core import publish_string, publish_parts
from docutils_tinyhtml import Writer

def rst2html(rst):
    writer = Writer()
    # store full html output to html variable
    html = publish_string(source=rst,
                          writer=writer,
                          writer_name='html',
                          settings_overrides={'link': 'link', 'top': 'top'})
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
            flash(_('Process is taking too long and will be terminated!'), 'error')
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

