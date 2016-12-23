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

def get_git(project, branch):
    repo_path = join('repos', project, branch, 'source')
    repo = git.Repo(repo_path)
    return repo.git

def load_file(path):
    with codecs.open(path, 'r', 'utf-8') as content_file:
        return content_file.read()

def write_file(path, contents):
    UTF8Writer = codecs.getwriter('utf8')
    with open(path, 'w') as dest_file:
        dest_file.write(contents.encode('utf8'))

def get_merging(project, branch):
    merge_file_path = join('repos', project, branch, 'merging.json')
    if isfile(merge_file_path):
        return json.loads(load_file(merge_file_path))

def get_requests(project, branch):
    git_api = get_git(project, branch)
    branches = string.split(git_api.branch())
    merged = string.split(git_api.branch('--merged'))
    unmerged = [item for item in branches if item not in merged]
    return unmerged

def get_merge_pendencies(project, branch):
    branch_repo_path = join('repos', project, branch)
    # user is merging?
    merging = get_merging(project, branch)
    if merging:
        return redirect(url_for('.merge', project=project,
                                branch=branch, other=merging['branch']))

def config_repo(repo, user_name, email):
    config = repo.config_writer()
    config.set_value('user', 'email', email)
    config.set_value('user', 'name', user_name)

def is_dirty(project, branch):
    repo_path = join('repos', project, branch, 'source')
    return git.Repo(repo_path).is_dirty()

def get_log(project, branch):
    git_api = get_git(project, branch)
    return git_api.log('-15', '--no-merges', '--abbrev-commit','--decorate', '--full-history',
                       "--format=format:%w(65,0,9)%an (%ar): %s %d", '--all')

def get_log_diff(project, origin, branch):
    git_api = get_git(project, origin)
    return git_api.log(origin + '..' + branch, '--graph',
                       '--abbrev-commit','--decorate', '--right-only',
                       "--format=format:%an (%ar): %s %d")

import subprocess
import arrow
import os

def last_modified(project, branch):
    branch_source_path = os.path.abspath(join('repos', project, branch, 'source'))
    command = 'find ' + branch_source_path + ' -printf "%TY-%Tm-%Td %TT\n" | sort -nr | head -n 1'
    timestamp = arrow.get(subprocess.check_output(command, shell=True))
    return(timestamp.humanize())

