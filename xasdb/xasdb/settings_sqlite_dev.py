from xasdb.settings import *
from xasdb.settings import BASE_DIR
import os

SECRET_KEY = 'jrr&b&3bqx6uxs^nf1wt2_36ky0w+e!yo$c8$h*m=mi_)c+!y6'

DEBUG = True

# for use in K8s with configmap object which defines ALLOWED_HOSTS env variable, which it turn must be a K8s service IP
# When DEBUG is True and ALLOWED_HOSTS is empty, the host is validated only against ['.localhost', '127.0.0.1', '[::1]']
ALLOWED_HOSTS = [os.environ.get('SERVICE_HOST')]

# # for use in local run
# # When DEBUG is True and ALLOWED_HOSTS is empty, the host is validated only against ['.localhost', '127.0.0.1', '[::1]']
# ALLOWED_HOSTS = []

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

