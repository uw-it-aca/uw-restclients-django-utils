# Django utilities for supporting UW REST Clients

[![Build Status](https://github.com/uw-it-aca/uw-restclients-django-utils/workflows/tests/badge.svg)](https://github.com/uw-it-aca/uw-restclients-django-utils/actions)
[![Coverage Status](https://coveralls.io/repos/uw-it-aca/uw-restclients-django-utils/badge.svg?branch=main)](https://coveralls.io/r/uw-it-aca/uw-restclients-django-utils?branch=main)
[![PyPi Version](https://img.shields.io/pypi/v/uw-restclients-django-utils.svg)](https://pypi.python.org/pypi/uw-restclients-django-utils)
![Python versions](https://img.shields.io/badge/python-3.10-blue.svg)


This project uses a function defined in your app to control access to the restclient proxy views, configured as RESTCLIENTS_ADMIN_AUTH_MODULE in your settings.py.

     RESTCLIENTS_ADMIN_AUTH_MODULE = 'your_app.module.can_proxy_restclient'

This function is passed three arguments, and should return True or False.

     can_proxy_restclient(request, service, url)

