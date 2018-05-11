# uw-restclients-django-utils
Django utilities for enhancing uw-restclients clients

This project uses a function defined in your app to control access to the restclient proxy views, configured as RESTCLIENTS_ADMIN_AUTH_MODULE in your settings.py.

     RESTCLIENTS_ADMIN_AUTH_MODULE = 'your_app.module.can_proxy_restclient'

This function is passed three arguments, and should return True or False.
 
     can_proxy_restclient(request, service, url)
     
