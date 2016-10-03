


## Update database

    python manage.py db migrate
    python manage.py db upgrade

## Init translations

In the applications folder

    pybabel extract -F babel.cfg -o messages.pot .

    pybabel init -i messages.pot -d translations -l de

    pybabel compile -d translations

## Init translations

    pybabel extract -F babel.cfg -o messages.pot .

    pybabel update -i messages.pot -d translations

    pybabel compile -d translations
