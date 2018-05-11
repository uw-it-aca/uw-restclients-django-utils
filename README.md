# uw-restclients-django-utils
Django utilities for enhancing uw-restclients clients

This project uses a function "is_admin()" defined in your app to control access to the user override app. It finds it via RC_DJANGO_ADMIN_AUTH_MODULE in your setting.py:

     RC_DJANGO_ADMIN_AUTH_MODULE = 'your_app.module.is_admin'

