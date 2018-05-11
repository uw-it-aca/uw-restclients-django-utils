# uw-restclients-django-utils
Django utilities for enhancing uw-restclients clients

This project uses a function defined in your app to control access to the restclient proxy views. It finds it via RESTCLIENTS_ADMIN_AUTH_MODULE in your setting.py:

     RESTCLIENTS_ADMIN_AUTH_MODULE = 'your_app.module.can_proxy_restclient'

