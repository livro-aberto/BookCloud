import sys

sys.path.insert(0, '/var/www/BookCloud')

#from application import app as application

from application import create_app

application = create_app()

