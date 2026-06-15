"""
Settings package initializer.
Imports from the appropriate environment settings module.
Default to development settings.
"""
import os

environment = os.environ.get('DJANGO_ENV', 'development')

if environment == 'production':
    from .prod import *  # noqa: F401, F403
else:
    from .dev import *  # noqa: F401, F403
