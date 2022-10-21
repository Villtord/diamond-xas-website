#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    # # for local run with sqlite db load env variables from file by uncommenting
    # env_file = 'env_settings_local.txt'
    # with open(env_file) as f:
    #     for line in f:
    #         if not line.startswith('#'):
    #             key, value = line.strip().split(':',1)
    #             os.environ[key.strip()] = value.strip()
    # uncomment until here
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", os.environ.get("DJANGO_SETTINGS_MODULE"))
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)
