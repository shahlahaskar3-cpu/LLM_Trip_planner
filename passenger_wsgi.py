import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Django_app'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Django_app.settings')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
