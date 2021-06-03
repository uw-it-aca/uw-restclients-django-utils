# Copyright 2021 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from rc_django.views import RestView
from rc_django.models import DegradePerformance


class DegradePerformanceView(RestView):
    template_name = "cause_errors.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        problem_str = kwargs.get("problem")
        problems = DegradePerformance(serialized=problem_str)

        context["errors"] = []
        for service in problems.services():
            context["errors"].append({
                "name": service,
                "status": problems.get_status(service),
                "content": problems.get_content(service),
                "load_time": problems.get_load_time(service),
            })
        return context

    def get(self, request, *args, **kwargs):
        kwargs["problem"] = request.session.get("RESTCLIENTS_ERRORS")
        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        problem_str = request.session.get("RESTCLIENTS_ERRORS")
        problems = DegradePerformance(serialized=problem_str)

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
            problems.set_status(
                key, request.POST.get("new_service_status", None))
            problems.set_content(
                key, request.POST.get("new_service_content", None))
            problems.set_load_time(
                key, request.POST.get("new_service_load_time", None))

        request.session["RESTCLIENTS_ERRORS"] = problems.serialize()
        kwargs["problem"] = request.session["RESTCLIENTS_ERRORS"]

        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)
