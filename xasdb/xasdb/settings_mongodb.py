from xasdb.settings import *
import os

# # for local run to check if mongodb works at all
# os.environ['MONGO_DB_HOST']='172.23.169.21'
# os.environ['MONGO_DB_PORT']='27017'
# os.environ['MONGO_INITDB_ROOT_USERNAME']='MongoXasDbAdmin'
# os.environ['MONGO_INITDB_ROOT_PASSWORD']='MongoXasDbPassword2022'

ALLOWED_HOSTS = [os.environ.get('ALLOWED_HOSTS')]

DATABASES = {
        'default': {
            'ENGINE': 'djongo',
            'NAME': 'xasdb',
            'ENFORCE_SCHEMA': False,
            'CLIENT': {
                'host': os.environ.get('MONGO_DB_HOST'),
                'port': int(os.environ.get('MONGO_DB_PORT')),
                'username': os.environ.get('MONGO_INITDB_ROOT_USERNAME'),
                'password': os.environ.get('MONGO_INITDB_ROOT_PASSWORD')
            },
            # 'LOGGING': {
            #     'version': 1,
            #     'loggers': {
            #         'djongo': {
            #             'level': 'DEBUG',
            #             'propagate': True,
            #         }
            #     },
            # },
        }
}