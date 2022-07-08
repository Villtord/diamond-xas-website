from xasdb.settings import *
import os

SECRET_KEY = 'jrr&b&3bqx6uxs^nf1wt2_36ky0w+e!yo$c8$h*m=mi_)c+!y6'

DEBUG = True

ALLOWED_HOSTS = []

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'xasdb',
        'PASSWORD': os.environ['XASDB_MARIADB_PASSWORD'],
        'USER': 'xas_db_usr',
        'OPTIONS': {
            'sql_mode': 'STRICT_TRANS_TABLES'
        },
    }
}


