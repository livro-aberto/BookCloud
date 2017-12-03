# BookCloud

A collaborative platform to write books based on git


## Install requisites

These are some installation instructions (for Ubuntu or Debian):

    sudo apt-get install python python-pip python-dev python-virtualenv

    sudo apt-get install libapache2-mod-wsgi

    sudo apt-get install poppler-utils

    sudo apt-get install libffi-dev libssl-dev python-bcrypt


For Debian 8:

    sudo apt-get install libmysqlclient-dev
    sudo apt-get install npm

For Debian 9:

    sudo apt-get install libmariadbclient-dev

Clone this repository, enter the BookCloud folder and create the virtual environment:

    virtualenv vir
    source vir/bin/activate
    pip install --upgrade pip
    pip install --upgrade setuptools

Then install the python requirements:

    pip install -r requirements.txt

Type `deactivate` if you want to exit the virtualenv.


## To install sql

Install the database

On Debian 8:


    sudo apt-get install mysql mysql-server

On Debian 9:

    sudo apt-get install mariadb-client mariadb-server

Add a root password. First login as root (which may have to be run under sudo):

    mysql -u root -p

Create a new user for bookcloud

    CREATE USER 'bookclouduser'@'localhost' IDENTIFIED BY '<password>';

Create a new database

    CREATE DATABASE bookcloud;


Grant user access to the database. To simplify, you can grant access to anything:

    GRANT ALL PRIVILEGES ON bookcloud . * TO 'bookclouduser'@'localhost';
    FLUSH PRIVILEGES;

Log out with root (pressing `Ctr-D`), then thes the new user's login:

    mysql -u <newusersname> -p

## Configuring the app

Create config file for sphinx:

    cp conf/conf_default.py conf/conf.py

and check there all the parameters you would like to change for the compilation.

Now create the config for the app

    cp instance/instance_config_default.py instance/instance_config.py

and edit the `instance/instance_config.py` file. Specially:

  1. Change your secret key
  2. Setup your email

## Create all tables in database

Remember to enter the virtual environment if not yet there:

    source vir/bin/activate

Enter the `migrations` folder and type

    alembic upgrade head

You could get an error of package not found if your alembic is installed system-wide (thus it will not find the packages in the virtual environment). In this case run

    python -m alembic.config upgrade head

## Install JavaScript requirements

First install bower

    sudo npm install -g bower

Then go to folder `application/static/vendor` and try

    bower install

If you get `/usr/bin/env: node: No such file or directory`, then you may have to change the name of the executable for node.js like that:

    sudo ln -s /usr/bin/nodejs /usr/bin/node

## Add translations

You may need:

    source vir/bin/activate

Then in `application` folder type:

    pybabel compile -d translations

# Server installation with nginx

## Installing uwsgi for nginx

I suggest reading this: `http://uwsgi-docs.readthedocs.io/en/latest/WSGIquickstart.html`.

First install gunicorn

    source vir/bin/activate
    pip install uwsgi

Test the application using

    uwsgi --http :9090 --wsgi-file wsgi.py

And from another terminal

    curl 0.0.0.0:9090

## Config

Check the configuration of uwsgi in `uwsgi.ini`.

## Create a systemd service for uwsgi

Edit the file:

    sudo nano /etc/systemd/system/uwsgi.service

And add this to the contents:

    [Unit]
    Description=uwsgi daemon
    After=network.target

    [Service]
    User=<user-name>
    Group=www-data
    WorkingDirectory=/var/www/BookCloud
    ExecStart=/var/www/BookCloud/vir/bin/uwsgi /var/www/BookCloud/uwsgi.ini
    Restart=always
    KillSignal=SIGQUIT
    Type=notify
    StandardError=syslog
    NotifyAccess=all

    [Install]
    WantedBy=multi-user.target

Replacing `/var/www/` by the location of your BookCloud folder.

Test it with:

    sudo systemctl start uwsgi
    sudo systemctl status uwsgi

If it is working, enable it

    sudo systemctl enable uwsgi

## Configure Nginx as a reverse proxy

Create a site file:

    sudo nano /etc/nginx/sites-available/BookCloud

Add the


# Redirect HTTP traffic to HTTPS

    server {
        listen 80;
        server_name www.umlivroaberto.org;
        rewrite ^/(.*) https://www.umlivroaberto.org/$1 permanent;
    }


# Default server configuration

Use this configuration for nginx (helps with reverse proxying the subpath):

    server {
        # SSL configuration

        listen 443 ssl;
        listen [::]:443 ssl;

        server_name www.umlivroaberto.org;

        ssl_certificate /etc/ssl/private/www_umlivroaberto_org.crt;
        ssl_certificate_key /etc/ssl/private/umlivroaberto.org.key;

        ssl_protocols TLSv1 TLSv1.1 TLSv1.2;
        ssl_prefer_server_ciphers on;
        ssl_ciphers 'EECDH+AESGCM:EDH+AESGCM:AES256+EECDH:AES256+EDH';


        location /BookCloud/ {
            include uwsgi_params;
            uwsgi_pass 127.0.0.1:3031;
        }
    }

Enable it:

    sudo ln -s /etc/nginx/sites-available/BookCloud /etc/nginx/sites-enabled/BookCloud

Test if the configuration worked:

    sudo nginx -t

Restart nginx:

    sudo systemctl restart nginx

And test it from outside.


