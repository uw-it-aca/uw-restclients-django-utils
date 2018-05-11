from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.utils.module_loading import import_string
from django.shortcuts import render


def can_proxy_restclient(request, *args, **kwargs):
    print("Your application should define an authorization function "
          "as RESTCLIENTS_ADMIN_AUTH_MODULE in settings.py.")
    return False


def restclient_admin_required(view_func):
    """
    Calls login_required in case the user is not authenticated.
    """
    def wrapper(request, *args, **kwargs):
        try:
            auth_func = import_string(settings.RESTCLIENTS_ADMIN_AUTH_MODULE)
        except (KeyError, ImportError):
            auth_func = can_proxy_restclient

        if auth_func(request, *args, **kwargs):
            return view_func(request, *args, **kwargs)

        return render(request, 'rc_django/access_denied.html', status=401)

    return login_required(function=wrapper)
