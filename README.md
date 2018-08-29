[![Build Status](https://api.travis-ci.org/uw-it-aca/uw-restclients-django-utils.svg?branch=master)](https://travis-ci.org/uw-it-aca/uw-restclients-django-utils)
[![Coverage Status](https://coveralls.io/repos/uw-it-aca/uw-restclients-django-utils/badge.png?branch=master)](https://coveralls.io/r/uw-it-aca/uw-restclients-django-utils?branch=master)

# uw-restclients-django-utils
Django utilities for enhancing uw-restclients clients

This project uses a function defined in your app to control access to the restclient proxy views, configured as RESTCLIENTS_ADMIN_AUTH_MODULE in your settings.py.

     RESTCLIENTS_ADMIN_AUTH_MODULE = 'your_app.module.can_proxy_restclient'

This function is passed three arguments, and should return True or False.
 
     can_proxy_restclient(request, service, url)
     
