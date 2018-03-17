#! /bin/bash

source vir/bin/activate

#( sleep 3 ; celery worker -A tests.celery_test_factory.celery ) &

py.test -s tests/

deactivate

rm /tmp/bookcloud_test.db

kill 0




