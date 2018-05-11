from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.utils.module_loading import import_string
from django.shortcuts import render


def can_proxy_restclient(request, service, url):
    print("Your application should define an authorization function "
          "as RESTCLIENTS_ADMIN_AUTH_MODULE in settings.py.")
    return False


def restclient_admin_required(view_func):
    """
    View decorator that checks whether the user is permitted to view proxy
    restclients. Calls login_required in case the user is not authenticated.
    """
    def wrapper(request, *args, **kwargs):
        if hasattr(settings, 'RESTCLIENTS_ADMIN_AUTH_MODULE'):
            auth_func = import_string(settings.RESTCLIENTS_ADMIN_AUTH_MODULE)
        else:
            auth_func = can_proxy_restclient

        service = args[0] if len(args) > 0 else None
        url = args[1] if len(args) > 1 else None
        if auth_func(request, service, url):
            return view_func(request, *args, **kwargs)

        return render(request, 'access_denied.html', status=401)

    return login_required(function=wrapper)
