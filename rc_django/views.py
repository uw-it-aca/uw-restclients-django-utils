import re
import json
import logging
import traceback
from django.conf import settings
from django.urls import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader, RequestContext, TemplateDoesNotExist
from django.shortcuts import render
from django.views.decorators.csrf import csrf_protect
from importlib import import_module
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
def proxy(request, service, url):
    user_service = UserService()
    actual_user = user_service.get_original_user()

    use_pre = False
    headers = {}

    if re.match(r'^iasystem', service):
        if url.endswith('/evaluation'):
            index = url.find('/')
            service = 'iasystem_' + url[:index].replace("_", "-")
            index += 1
            url = url[index:]
            headers["Accept"] = "application/vnd.collection+json"
    elif service == "libcurrics":
            if "?campus=" in url:
                url = url.replace("?campus=", "/")
            elif "course?" in url:
                url_prefix = re.sub(r'\?.*$', "", url)
                url = "%s/%s/%s/%s/%s/%s" % (
                    url_prefix,
                    request.GET["year"],
                    request.GET["quarter"],
                    request.GET["curriculum_abbr"],
                    request.GET["course_number"],
                    request.GET["section_id"])
    elif service == "sws" or service == "gws":
        headers["X-UW-Act-as"] = actual_user
    elif service == "calendar":
        use_pre = True

    try:
        service_name = service
        if service == 'iasystem':
            service_name = 'iasystem_uw'
        dao = get_dao_instance(service_name)
    except (AttributeError, ImportError):
        return HttpResponse("Missing service: %s" % service,
                            status=404)

    url = "/%s" % quote(url)

    if request.GET:
        try:
            url = "%s?%s" % (url, urlencode(request.GET))
        except UnicodeEncodeError as err:
            return HttpResponse(
                'Bad URL param given to the restclients browser')

    response, start, end = get_response(request, service, url, headers, dao)

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
            content = format_json(service, response.data)
            json_data = response.data
        except ValueError:
            content = format_html(service, response.data)

    context = {
        "url": unquote(url),
        "content": content,
        "json_data": json_data,
        "response_code": response.status,
        "time_taken": "%f seconds" % (end - start),
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
        search_template = "proxy/%s%s.html" % (service, search_template_path)
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
    json_data = json.loads(content)
    formatted = json.dumps(json_data, sort_keys=True, indent=4)
    formatted = formatted.replace("&", "&amp;")
    formatted = formatted.replace("<", "&lt;")
    formatted = formatted.replace(">", "&gt;")
    formatted = formatted.replace(" ", "&nbsp;")
    formatted = formatted.replace("\n", "<br/>\n")

    base_url = reverse("restclients_proxy", args=["xx", "xx"])
    base_url = base_url.replace('/xx/xx', '')

    formatted = re.sub(r"\"/(.*?)\"",
                       r'"<a href="%s/%s/\1">/\1</a>"' % (base_url, service),
                       formatted)

    return formatted


def format_html(service, content):
    base_url = reverse("restclients_proxy", args=["xx", "xx"])
    base_url = base_url.replace('/xx/xx', '')

    formatted = re.sub(r"href\s*=\s*\"/(.*?)\"",
                       r'href="%s/%s/\1"' % (base_url, service), content)
    formatted = re.sub(re.compile(r"<style.*/style>", re.S), "", formatted)
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
            keepit = "keep_%s" % key
            if keepit not in request.POST:
                problems.remove_service(key)
            else:
                problems.set_status(key,
                                    request.POST.get("%s_status" % key, None))
                problems.set_content(key,
                                     request.POST.get("%s_content" % key,
                                                      None))
                problems.set_load_time(key,
                                       request.POST.get("%s_load_time" % key,
                                                        None))

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
