# BookCloud

A collaborative platform to write books based on git


## Installation

These are some installation instructions (for Debian):

    sudo apt-get install python python-pip python-dev python-virtualenv

    sudo apt-get install libapache2-mod-wsgi

    sudo apt-get install libffi-dev libssl-dev python-bcrypt

    virtualenv vir
    source vir/bin/activate

    pip install -r requirements.txt

Create config file

    cp conf_default.py conf.py

    cp conf/conf_default.py conf/conf.py

edit the `conf.py` file. Specially:

  1. Change your secret key
  2. Setup your email


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
