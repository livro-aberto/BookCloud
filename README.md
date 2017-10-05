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

Enter the virtual environment:

    source vir/bin/activate

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

    CREATE USER '<newusersname>'@'localhost' IDENTIFIED BY '<password>';

Grant user access to the database. To simplify, you can grant access to anything:

    GRANT ALL PRIVILEGES ON * . * TO '<newusersname>'@'localhost';
    FLUSH PRIVILEGES;

Log out with root (pressing `Ctr-D`), then log in with the new user:

    mysql -u <newusersname> -p

Create a new database

    CREATE DATABASE <databasename>;

Usually `bookcloud` is a good name for the database.

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

