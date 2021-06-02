# Copyright 2021 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.views.generic.base import TemplateView
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.template import loader, TemplateDoesNotExist
from rc_django.decorators import restclient_admin_required


@method_decorator(csrf_protect, name='dispatch')
@method_decorator(restclient_admin_required, name='dispatch')
class RestView(TemplateView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            loader.get_template("restclients/proxy_wrapper.html")
            context["wrapper_template"] = "restclients/proxy_wrapper.html"
        except TemplateDoesNotExist:
            context["wrapper_template"] = "proxy_wrapper.html"
        return context
