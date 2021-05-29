# Copyright 2021 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

import re
import json
import logging
import traceback
from django.urls import reverse
from django.http import HttpResponse
from django.template import loader, TemplateDoesNotExist
from django.shortcuts import render
from django.views.decorators.csrf import csrf_protect
from restclients_core.dao import DAO
from restclients_core.models import MockHTTP
from restclients_core.exceptions import DataFailureException
from rc_django.decorators import restclient_admin_required
from rc_django.models import DegradePerformance
from userservice.user import UserService
from time import time
from urllib.parse import quote, unquote, urlencode, urlparse, parse_qs
from base64 import b64encode


logger = logging.getLogger(__name__)


def set_wrapper_template(context):
    try:
        loader.get_template("restclients/proxy_wrapper.html")
        context["wrapper_template"] = "restclients/proxy_wrapper.html"
    except TemplateDoesNotExist:
        context["wrapper_template"] = "proxy_wrapper.html"


def get_dao_instance(service):
    def get_all_subclasses(base):
        return base.__subclasses__() + [g for s in base.__subclasses__()
                                        for g in get_all_subclasses(s)]

    for subclass in get_all_subclasses(DAO):
        dao = subclass()
        if dao.service_name() == service:
            return dao
    raise ImportError()


def get_response(request, service, url, headers, dao):
    start = time()
    try:
        response = dao.getURL(url, headers)
    except DataFailureException as ex:
        logger.error(str(ex))
        response = get_mock_response(ex)
    end = time()
    return response, start, end


def get_mock_response(ex):
    response = MockHTTP()
    response.status = ex.status
    response.data = ex.msg
    return response


@csrf_protect
@restclient_admin_required
def customform(request, service, url):
    headers = {}
    use_actual_user = True
    set_url_querystr = False
    logger.debug(
        "Enter customform service: {}, url: {}, GET: {}".format(
            service, url, request.GET))
    if url.endswith(".html") or len(request.GET) == 0:
        local_temp_url = "customform/{}/{}".format(service, url)
        context = {
            "local_template": local_temp_url,
        }
        set_wrapper_template(context)
        logger.debug("Exit customform context: {}".format(context))
        return render(request, "customform.html", context)

    elif service == "book":
        if "store" == url:
            url = "{}?quarter={}&sln1={}&returnlink=t".format(
                "uw/json_utf8_202007.ubs",
                request.GET["quarter"],
                request.GET["sln1"])
    elif service == "grad":
        set_url_querystr = True
    elif service == "hfs":
        if "accounts" in url:
            url = "myuw/v1/{}".format(request.GET["uwnetid"])
    elif re.match(r'^iasystem', service):
        if url.endswith('/evaluation'):
            index = url.find('/')
            service = 'iasystem_' + url[:index]
            index += 1
            url = url[index:]
            headers["Accept"] = "application/vnd.collection+json"
            set_url_querystr = True
    elif service == "myplan":
        if "plan" == url:
            url = "student/api/plan/v1/{},{},1,{}".format(
                request.GET["year"],
                request.GET["quarter"],
                request.GET["uwregid"])
    elif service == "libcurrics":
        if "course" == url:
            url = "currics_db/api/v1/data/course/{}/{}/{}/{}/{}".format(
                request.GET["year"],
                request.GET["quarter"],
                request.GET["curriculum_abbr"],
                request.GET["course_number"],
                request.GET["section_id"])
        elif "defaultGuide" == url:
            url = "currics_db/api/v1/data/defaultGuide/{}".format(
                request.GET["campus"])
    elif service == "libraries":
        if "accounts" == url:
            url = "mylibinfo/v1/?id={}&style=json".format(
                request.GET["uwnetid"])
    elif service == "sws":
        if "advisers" == url:
            url = "/student/v5/person/{}/advisers.json".format(
                request.GET["uwregid"])
    elif service == "uwnetid":
        if "password" == url:
            url = "nws/v1/uwnetid/{}/password".format(
                request.GET["uwnetid"])
        elif "subscription" == url:
            url = "nws/v1/uwnetid/{}/subscription/60,64,105".format(
                request.GET["uwnetid"])

    if set_url_querystr:
        try:
            url = "{}?{}".format(url, request.GET.urlencode())
        except UnicodeEncodeError as err:
            logger.error(
                "{} Bad URL params: {}".format(err, request.GET))
            return HttpResponse('Bad values in the form')

    return render_results(request, service, url, headers, use_actual_user)


@csrf_protect
@restclient_admin_required
def proxy(request, service, url):
    headers = {}
    use_actual_user = False

    logger.debug(
        "Enter proxy service: {}, url: {}, GET: {}".format(
            service, url, request.GET))

    if service == "sws" or service == "gws":
        use_actual_user = True

    if request.GET:
        try:
            url = "{}?{}".format(url, urlencode(request.GET))
        except UnicodeEncodeError as err:
            return HttpResponse(
                'Bad URL param given to the restclients browser')
    return render_results(request, service, url, headers, use_actual_user)


def render_results(request, service, url, headers, use_actual_user):
    logger.debug(
        "Enter render_results service: {}, url: {}, headers: {}".format(
            service, url, headers))
    use_pre = False
    if service == "calendar":
        use_pre = True

    user_service = UserService()
    if use_actual_user:
        headers["X-UW-Act-as"] = user_service.get_original_user()

    try:
        service_name = service
        if service == 'iasystem':
            service_name = 'iasystem_uw'
        dao = get_dao_instance(service_name)
    except (AttributeError, ImportError):
        return HttpResponse("Missing service: {}".format(service),
                            status=404)

    url = "/{}".format(quote(url))
    response, start, end = get_response(request, service, url, headers, dao)
    logger.debug("get_response url: {}, status: {}, data: {}".format(
        url, response.status, response.data))
    is_image = False
    base_64 = None
    json_data = None
    content = response.data
    # Handle known images
    if (response.status == 200 and
            re.match(r'/idcard/v1/photo/[0-9A-F]{32}', url)):
        is_image = True
        base_64 = b64encode(response.data)
    elif not use_pre:
        try:
            # Assume json, and try to format it.
            content, json_data = format_json(service, response.data)
        except ValueError:
            content = format_html(service, response.data)

    context = {
        "url": unquote(url),
        "content": content,
        "json_data": json_data,
        "response_code": response.status,
        "time_taken": "{:f} seconds".format(end - start),
        "headers": response.headers,
        "override_user": user_service.get_override_user(),
        "use_pre": use_pre,
        "is_image": is_image,
        "base_64": base_64,
    }

    try:
        loader.get_template("restclients/extra_info.html")
        context["has_extra_template"] = True
        context["extra_template"] = "restclients/extra_info.html"
    except TemplateDoesNotExist:
        pass

    set_wrapper_template(context)

    try:
        search_template_path = re.sub(r"[.?].*$", "", url)
        search_template = "proxy/{}{}.html".format(service,
                                                   search_template_path)
        loader.get_template(search_template)
        context["search_template"] = search_template
        context["search"] = format_search_params(url)
    except TemplateDoesNotExist:
        context["search_template"] = None

    return render(request, "proxy.html", context)


def format_search_params(url):
    params = {}
    query_params = parse_qs(urlparse(url).query)
    for param in query_params:
        params[param] = ",".join(query_params[param])
    return params


def format_json(service, content):
    data = json.loads(content)
    formatted = json.dumps(data, sort_keys=True, indent=4)
    formatted = formatted.replace("&", "&amp;")
    formatted = formatted.replace("<", "&lt;")
    formatted = formatted.replace(">", "&gt;")
    formatted = formatted.replace(" ", "&nbsp;")
    formatted = formatted.replace("\n", "<br/>\n")

    base_url = reverse("restclients_proxy", args=["xx", "xx"])
    base_url = base_url.replace('/xx/xx', '')

    formatted = re.sub(r"\"/(.*?)\"",
                       r'"<a href="{}/{}/\1">/\1</a>"'.format(base_url,
                                                              service),
                       formatted)

    return formatted, json.dumps(data, sort_keys=True)


def format_html(service, content):
    try:
        content = content.decode('utf-8')
    except AttributeError:
        pass

    base_url = reverse("restclients_proxy", args=["xx", "xx"])
    base_url = base_url.replace('/xx/xx', '')

    formatted = re.sub(r"href\s*=\s*[\"\']/(.*?)[\"\']",
                       r'href="{}/{}/\1"'.format(base_url, service),
                       content, flags=re.I)
    formatted = re.sub(
        re.compile(r"<style.*/style>", flags=re.S | re.I), "", formatted)
    formatted = clean_self_closing_divs(formatted)
    return formatted


def clean_self_closing_divs(content):
    cleaned = re.sub(r"((<div[^>]*?)/>)",
                     r"<!-- \g<1> -->\g<2>></div>",
                     content)
    return cleaned


@csrf_protect
@restclient_admin_required
def errors(request):
    context = {}
    context["errors"] = []
    problem_str = request.session.get("RESTCLIENTS_ERRORS", None)
    problems = DegradePerformance(serialized=problem_str)

    drop_keys = []
    if request.method == "POST":
        for key in problems.services():
            keepit = "keep_{}".format(key)
            if keepit not in request.POST:
                problems.remove_service(key)
            else:
                problems.set_status(
                    key, request.POST.get("{}_status".format(key), None))
                problems.set_content(
                    key, request.POST.get("{}_content".format(key), None))
                problems.set_load_time(
                    key, request.POST.get("{}_load_time".format(key), None))

        new_service = request.POST.get("new_service_name", None)
        if new_service:
            key = request.POST["new_service_name"]
            problems.set_status(key,
                                request.POST.get("new_service_status", None))
            problems.set_content(key,
                                 request.POST.get("new_service_content", None))
            problems.set_load_time(key,
                                   request.POST.get("new_service_load_time",
                                                    None))

        request.session["RESTCLIENTS_ERRORS"] = problems.serialize()

    for service in problems.services():
        context["errors"].append({
            "name": service,
            "status": problems.get_status(service),
            "content": problems.get_content(service),
            "load_time": problems.get_load_time(service),
        })

    set_wrapper_template(context)

    return render(request, "cause_errors.html", context)
