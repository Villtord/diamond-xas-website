from xasdb.settings import *
import os

SECRET_KEY = 'jrr&b&3bqx6uxs^nf1wt2_36ky0w+e!yo$c8$h*m=mi_)c+!y6'

DEBUG = True

ALLOWED_HOSTS = []

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

