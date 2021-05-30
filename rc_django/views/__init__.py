# Copyright 2021 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.shortcuts import render
from django.template import loader, TemplateDoesNotExist
from django.views.decorators.csrf import csrf_protect
from rc_django.decorators import restclient_admin_required
from rc_django.models import DegradePerformance


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

    try:
        loader.get_template("restclients/proxy_wrapper.html")
        context["wrapper_template"] = "restclients/proxy_wrapper.html"
    except TemplateDoesNotExist:
        context["wrapper_template"] = "proxy_wrapper.html"

    return render(request, "cause_errors.html", context)
