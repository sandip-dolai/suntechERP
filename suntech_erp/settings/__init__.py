from .base import *

if DJANGO_ENV == 'production':
    from .production import *
elif DJANGO_ENV == 'development':
    from .development import *
else:
    raise ValueError(f"Invalid DJANGO_ENV={DJANGO_ENV}")