# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.utils.deprecation import MiddlewareMixin
from restclients_core.util.performance import PerformanceDegradation
from rc_django.models import DegradePerformance


class EnableServiceDegradationMiddleware(MiddlewareMixin):
    """
    Makes it so an admin tool can set specific services to either be slower,
    have an error response code, or custom content.
    """
    def process_request(self, request):
        PerformanceDegradation.clear_problems()
        if "RESTCLIENTS_ERRORS" not in request.session:
            return

        problem_str = request.session["RESTCLIENTS_ERRORS"]
        problems = DegradePerformance(problem_str)
        PerformanceDegradation.set_problems(problems)

    def process_response(self, request, response):
        PerformanceDegradation.clear_problems()

        return response
