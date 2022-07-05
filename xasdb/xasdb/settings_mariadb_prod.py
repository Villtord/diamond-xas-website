from xasdb.xasdb.settings import *
import os
from django.core.management.utils import get_random_secret_key

STATICFILES_STORAGE = 'xasdb.utils.XASDBStaticFilesStorage'

DEBUG = False

ALLOWED_HOSTS = ['xasdb.diamond.ac.uk']

MEDIA_ROOT = '/dls/science/users/awf63395/xasdb/media/'

SECRET_DIR = os.path.join(BASE_DIR, 'config', 'secrets')
SECRET_FILE = os.path.join(SECRET_DIR, 'secret_key.cnf')

try:
    SECRET_KEY = open(SECRET_FILE).read().strip()
except Exception:
    # If the file doesn't exist, make it
    try:
        os.makedirs(SECRET_DIR, exist_ok=True)
        with open(SECRET_FILE, 'w+') as f:
            f.write(get_random_secret_key())
        SECRET_KEY = open(SECRET_FILE).read().strip()
    except Exception as e:
        raise Exception('Cannot open file `%s` for writing.' % SECRET_FILE)


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'OPTIONS': {
            'sql_mode': 'STRICT_TRANS_TABLES',
            'read_default_file': os.path.join(SECRET_DIR, 'database.cnf')
        },
    }
}


