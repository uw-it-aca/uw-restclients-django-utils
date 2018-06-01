import re
from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader, RequestContext, TemplateDoesNotExist
from django.shortcuts import render
from django.views.decorators.csrf import csrf_protect
from importlib import import_module
from restclients_core.dao import DAO
from restclients_core.models import MockHTTP
from rc_django.decorators import restclient_admin_required
from rc_django.models import DegradePerformance
from userservice.user import UserService
from time import time
try:
    from urllib.parse import quote, unquote, urlencode, urlparse, parse_qs
except ImportError:
    from urllib import quote, unquote, urlencode
    from urlparse import urlparse, parse_qs
from base64 import b64encode
import json
import re


def set_wrapper_template(context):
    try:
        loader.get_template("restclients/proxy_wrapper.html")
        context["wrapper_template"] = "restclients/proxy_wrapper.html"
    except TemplateDoesNotExist:
        context["wrapper_template"] = "proxy_wrapper.html"


def get_dao_instance(service):
    for subclass in DAO.__subclasses__():
        dao = subclass()
        if dao.service_name() == service:
            return dao
    raise ImportError()


@csrf_protect
@restclient_admin_required
def proxy(request, service, url):
    user_service = UserService()
    actual_user = user_service.get_original_user()

    use_pre = False
    headers = {}

    if service == "iasystem":
        headers["Accept"] = "application/vnd.collection+json"
        if url.endswith('/evaluation'):
            index = url.find('/')
            if index > -1:
                service = 'iasystem_' + url[:index].replace("_", "-")
                index += 1
                url = url[index:]
    try:
        dao = get_dao_instance(service)
    except (AttributeError, ImportError):
        return HttpResponse("Missing service: %s" % service, status=404)

    if service == "sws" or service == "gws":
        headers["X-UW-Act-as"] = actual_user
    elif service == "calendar":
        use_pre = True

    url = "/%s" % quote(url)

    if request.GET:
        try:
            url = "%s?%s" % (url, urlencode(request.GET))
        except UnicodeEncodeError as err:
            return HttpResponse(
                'Bad URL param given to the restclients browser')

    start = time()
    try:
        if service == "libcurrics":
            if "?campus=" in url:
                url = url.replace("?campus=", "/")
            elif "course?" in url:
                url_prefix = re.sub(r'\?.*$', "", url)
                url = "%s/%s/%s/%s/%s/%s" % (
                    url_prefix,
                    request.GET["year"],
                    request.GET["quarter"],
                    request.GET["curriculum_abbr"].replace(" ", "%20"),
                    request.GET["course_number"],
                    request.GET["section_id"])

        response = dao.getURL(url, headers)
    except Exception as ex:
        response = MockHTTP()
        response.status = 500
        response.data = str(ex)

    end = time()

    # First, check for known images
    is_image = False
    base_64 = None
    # Assume json, and try to format it.
    try:
        if url.find('/idcard/v1/photo') == 0:
            is_image = True
            base_64 = b64encode(response.data)
        if not use_pre:
            content = format_json(service, response.data)
            json_data = response.data
        else:
            content = response.data
            json_data = None
    except ValueError:
        content = format_html(service, response.data)
        json_data = None

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
    formatted = re.sub(r"href\s*=\s*\"/(.*?)\"",
                       r"href='/restclients/view/%s/\1'" % service, content)
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
