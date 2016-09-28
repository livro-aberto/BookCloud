


## Update database

    python manage.py db migrate
    python manage.py db upgrade

## Update translations

    pygettext -o /tmp/messages.pot  application/views.py
    msgmerge locale/pt_BR/LC_MESSAGES/messages.po /tmp/messages.pot > /tmp/final.po

edit the final file and put it in the right place (look for items marked fuzzy)

    msgfmt locale/pt_BR/LC_MESSAGES/messages.po -o locale/pt_BR/LC_MESSAGES/messages.mo
