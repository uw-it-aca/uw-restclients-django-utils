# Copyright 2021 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from rc_django.views import RestView
from rc_django.models import RestProxy
from django.template import loader, TemplateDoesNotExist
from django.urls import reverse
from django.http import HttpResponse, HttpResponseRedirect
from userservice.user import UserService
from urllib.parse import quote, unquote, urlencode, urlparse, parse_qs
from base64 import b64encode
from logging import getLogger
import re

logger = getLogger(__name__)


class RestProxyView(RestView):
    template_name = "proxy.html"

    @staticmethod
    def format_search_params(url):
        params = {}
        query_params = parse_qs(urlparse(url).query)
        for param in query_params:
            params[param] = ",".join(query_params[param])
        return params

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        service = kwargs.get("service")
        url = kwargs.get("url")
        headers = kwargs.get("headers", {})
        service_name = service
        use_pre = False
        is_image = False
        user_service = UserService()

        if service == "iasystem":
            headers["Accept"] = "application/vnd.collection+json"
            service_name = 'iasystem_uw'
        elif service == "sws" or service == "gws":
            headers["X-UW-Act-as"] = user_service.get_original_user()
        elif service == "calendar":
            use_pre = True

        proxy = RestProxy(service_name)
        response = proxy.get_api_response(url, headers)

        if (response.status == 200 and
                re.match(r"/idcard/v1/photo/[0-9A-F]{32}", url)):
            # Handle known images
            is_image = True
            content = b64encode(response.data).decode("utf-8")
        elif use_pre:
            content = response.data
        else:
            content = proxy.formatted

        context.update({
            "url": unquote(url),
            "content": content,
            "json_data": proxy.json,
            "response_code": response.status,
            "time_taken": "{:f} seconds".format(proxy.duration),
            "headers": response.headers,
            "override_user": user_service.get_override_user(),
            "use_pre": use_pre,
            "is_image": is_image,
        })

        try:
            loader.get_template("restclients/extra_info.html")
            context["has_extra_template"] = True
            context["extra_template"] = "restclients/extra_info.html"
        except TemplateDoesNotExist:
            pass

        try:
            search_template_path = re.sub(r"[.?].*$", "", url)
            search_template = "proxy/{}{}.html".format(service,
                                                       search_template_path)
            loader.get_template(search_template)
            context["search_template"] = search_template
            context["search"] = self.format_search_params(url)
        except TemplateDoesNotExist:
            context["search_template"] = None

        return context

    def get(self, request, *args, **kwargs):
        """
        Fetch an API resource and render it, formatted for a browser.
        """
        # Using args for these URLs for backwards-compatibility
        kwargs["service"] = args[0]
        kwargs["url"] = "/" + (args[1] if len(args) > 1 else "")

        if request.GET:
            kwargs["url"] += "?" + urlencode(request.GET)
        else:
            try:
                path, qs = kwargs["url"].split("?")
                kwargs["url"] = "?".join([quote(path), qs])
            except ValueError:
                pass

        try:
            context = self.get_context_data(**kwargs)
        except (AttributeError, ImportError):
            return HttpResponse(
                "Missing service: {}".format(kwargs["service"]), status=404)

        return self.render_to_response(context)


class RestSearchView(RestView):
    template_name = "customform.html"
    form_action_url = "restclients_customform"

    def get_context_data(self, **kwargs):
        service = kwargs.get("service")
        path = kwargs.get("path", "")

        context = super().get_context_data(**kwargs)

        form_path = "customform/{}/{}".format(service, path)
        try:
            loader.get_template("restclients/{}".format(form_path))
            context["form_template"] = "restclients/{}".format(form_path)
        except TemplateDoesNotExist:
            loader.get_template(form_path)
            context["form_template"] = form_path

        context["form_action"] = reverse(self.form_action_url, args=[
            service, path.replace(".html", "")])
        return context

    def get(self, request, *args, **kwargs):
        """
        Renders a custom form for searching a REST service.
        """
        # Using args for these URLs for backwards-compatibility
        kwargs["service"] = args[0]
        kwargs["path"] = args[1] if len(args) > 1 else ""

        try:
            context = self.get_context_data(**kwargs)
        except TemplateDoesNotExist as ex:
            return HttpResponse("Missing template: {}".format(ex), status=404)

        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        """
        Entry point for custom search form submissions.
        Convert form data to actual API urls, and redirect to proxy view.
        """
        service = args[0]
        url = args[1] if len(args) > 1 else ""

        try:
            service, url, params = self.get_proxy_url(request, service, url)
        except KeyError as ex:
            return HttpResponse("Missing reqired form value: {}".format(ex),
                                status=400)

        url = reverse("restclients_proxy", args=[service, url])
        if params:
            url += "?" + urlencode(params)
        return HttpResponseRedirect(url)

    def format_params(self, request):
        return {k: v for k, v in request.POST.items() if (
            k != "csrfmiddlewaretoken")}

    def get_proxy_url(self, request, service, url):
        params = None
        if service == "libcurrics":
            if "course" == url:
                url = "currics_db/api/v1/data/{}/{}/{}/{}/{}/{}".format(
                    "course",
                    request.POST["year"],
                    request.POST["quarter"],
                    request.POST["curriculum_abbr"],
                    request.POST["course_number"],
                    request.POST["section_id"])
            elif "default" == url:
                url = "currics_db/api/v1/data/defaultGuide/{}".format(
                    request.POST["campus"])
        elif service == "libraries":
            url = "mylibinfo/v1/"
            params = self.format_params(request)

        return service, url, params
