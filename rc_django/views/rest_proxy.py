# Copyright 2021 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.views.generic.base import TemplateView
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from django.template import loader, TemplateDoesNotExist
from django.http import HttpResponse
from urllib.parse import quote, unquote, urlencode, urlparse, parse_qs
from rc_django.decorators import restclient_admin_required
from rc_django.models import RestProxy
from userservice.user import UserService
from base64 import b64encode
import re
import logging

logger = logging.getLogger(__name__)


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


class RestSearchView(RestView):
    template_name = "customform.html"

    def get_context_data(self, **kwargs):
        service = kwargs.get("service")
        path = kwargs.get("path")

        context = super().get_context_data(**kwargs)
        context["local_template"] = "customform/{}/{}".format(service, path)
        return context

    def get(self, request, *args, **kwargs):
        # Using args for these URLs for backwards-compatibility
        kwargs["service"] = args[0]
        kwargs["url"] = args[1] if len(args) > 1 else ""
        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)


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
        url = kwargs.get("url", "")
        headers = kwargs.get("headers", {})
        user_service = UserService()

        if kwargs.get("actas_user"):
            headers["X-UW-Act-as"] = user_service.get_original_user()

        url = "/{}".format(quote(url))
        service_name = service
        if service == 'iasystem':
            service_name = 'iasystem_uw'

        proxy = RestProxy(service_name)
        response = proxy.get_api_response(url, headers)

        # logger.debug("get_api_response url: {}, status: {}, data: {}".format(
        #    url, response.status, response.data))

        use_pre = True if (service == "calendar") else False
        is_image = False

        if (response.status == 200 and
                re.match(r'/idcard/v1/photo/[0-9A-F]{32}', url)):
            # Handle known images
            is_image = True
            content = b64encode(response.data)
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
            context["search"] = format_search_params(url)
        except TemplateDoesNotExist:
            context["search_template"] = None

        return context

    def get(self, request, *args, **kwargs):
        """
        The proxy view for API URLs.
        """
        # Using args for these URLs for backwards-compatibility
        service = args[0]
        url = args[1] if len(args) > 1 else ""

        if service == "sws" or service == "gws":
            kwargs["actas_user"] = True

        if request.GET:
            try:
                url = "{}?{}".format(url, urlencode(request.GET))
            except UnicodeEncodeError as err:
                return HttpResponse(
                    'Bad URL param given to the restclients browser')

        kwargs["service"] = service
        kwargs["url"] = url
        try:
            context = self.get_context_data(**kwargs)
        except (AttributeError, ImportError):
            return HttpResponse("Missing service: {}".format(service),
                                status=404)

        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        """
        Entry point for custom search forms, converts form data to actual
        API URLs.
        """
        service = args[0]
        url = args[1] if len(args) > 1 else ""
        headers = {}

        set_url_querystr = False
        try:
            if service == "book":
                if "store" == url:
                    url = "{}?quarter={}&sln1={}&returnlink=t".format(
                        "uw/json_utf8_202007.ubs",
                        request.POST["quarter"],
                        request.POST["sln1"])
            elif service == "grad":
                set_url_querystr = True
            elif service == "hfs":
                if "accounts" in url:
                    url = "myuw/v1/{}".format(request.POST["uwnetid"])
            elif re.match(r'^iasystem', service):
                if url.endswith('/evaluation'):
                    index = path.find('/')
                    service = 'iasystem_' + url[:index]
                    index += 1
                    url = url[index:]
                    headers["Accept"] = "application/vnd.collection+json"
                    set_url_querystr = True
            elif service == "myplan":
                if "plan" == url:
                    url = "student/api/plan/v1/{},{},1,{}".format(
                        request.POST["year"],
                        request.POST["quarter"],
                        request.POST["uwregid"])
            elif service == "libcurrics":
                if "course" == url:
                    url = "currics_db/api/v1/data/{}/{}/{}/{}/{}/{}".format(
                        "course",
                        request.POST["year"],
                        request.POST["quarter"],
                        request.POST["curriculum_abbr"],
                        request.POST["course_number"],
                        request.POST["section_id"])
                elif "defaultGuide" == path:
                    url = "currics_db/api/v1/data/defaultGuide/{}".format(
                        request.POST["campus"])
            elif service == "libraries":
                if "accounts" == url:
                    url = "mylibinfo/v1/?id={}".format(
                        request.POST["uwnetid"])
            elif service == "sws":
                if "advisers" == url:
                    url = "/student/v5/person/{}/advisers.json".format(
                        request.POST["uwregid"])
            elif service == "uwnetid":
                if "password" == url:
                    url = "nws/v1/uwnetid/{}/password".format(
                        request.POST["uwnetid"])
                elif "subscription" == url:
                    url = "nws/v1/uwnetid/{}/subscription/60,64,105".format(
                        request.POST["uwnetid"])
        except KeyError as ex:
            return HttpResponse('Missing reqired form value: {}'.format(ex),
                                status=400)

        if set_url_querystr:
            try:
                url = "{}?{}".format(url, request.POST.urlencode())
            except UnicodeEncodeError as err:
                logger.error(
                    "{} Bad URL params: {}".format(err, request.POST))
                return HttpResponse('Bad values in the form', status=400)

        kwargs["service"] = service
        kwargs["url"] = url
        kwargs["headers"] = headers

        try:
            context = self.get_context_data(**kwargs)
        except (AttributeError, ImportError):
            return HttpResponse("Missing service: {}".format(service),
                                status=404)

        return self.render_to_response(context)
