import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'vvs.settings'
os.environ['PYTHON_EGG_CACHE'] = '/tmp/www-python-eggs'

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
