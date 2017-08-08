# BookCloud

A collaborative platform to write books based on git


## Installation

These are some installation instructions (for Ubuntu or Debian):

    sudo apt-get install python python-pip python-dev python-virtualenv

    sudo apt-get install libapache2-mod-wsgi

    sudo apt-get install poppler-utils npm

    sudo apt-get install mysql-server libmysqlclient-dev

    sudo apt-get install libffi-dev libssl-dev python-bcrypt

    virtualenv vir
    source vir/bin/activate

when needed use `deactivate` to exit the virtualenv

    pip install -r requirements.txt

Create config file

    cp config_default.py config.py

    cp conf/conf_default.py conf/conf.py

    cp cp instance/instance_config_default.py instance/instance_config.py

edit the `conf.py` file. Specially:

  1. Change your secret key
  2. Setup your email

## Bower installation

First install bower

    sudo npm install -g bower



Then go to folder `application/static/vendor` and try `bower install`. If you get `/usr/bin/env: node: No such file or directory`, then you may have to change the name of the executable for node.js like that:

    sudo ln -s /usr/bin/nodejs /usr/bin/node

## To install sql

Install

    sudo apt-get install mysql

add a root password

    login as root
    mysql -u root -p

create a new user

    CREATE USER 'newusersname'@'localhost' IDENTIFIED BY 'password';

grant user access to anything

    GRANT ALL PRIVILEGES ON * . * TO 'newusersname'@'localhost';
    FLUSH PRIVILEGES;

log out with root (Ctr-D) log in with user

    mysql -u newusersname -p

create a new database

    CREATE DATABASE databasename;

## Notation


users: @john
branches: _fixing
files: #intro


## Add instructions for locale compilation
