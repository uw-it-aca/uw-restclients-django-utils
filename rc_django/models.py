# Copyright 2021 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.db import models
from django.urls import reverse
from restclients_core.dao import DAO
from restclients_core.models import MockHTTP
from restclients_core.exceptions import DataFailureException
from time import time
import json
import re


class RestProxy():
    def __init__(self, service):
        self.service = service
        self.response = None
        self._request_start = 0
        self._request_end = 0

    @property
    def dao(self):
        def get_all_subclasses(base):
            return base.__subclasses__() + [g for s in base.__subclasses__()
                                            for g in get_all_subclasses(s)]

        for subclass in get_all_subclasses(DAO):
            dao = subclass()
            if dao.service_name() == self.service:
                return dao
        raise ImportError()

    @property
    def duration(self):
        return self._request_end - self._request_start

    @property
    def json(self):
        try:
            return json.dumps(json.loads(self.response.data), sort_keys=True)
        except ValueError:
            pass

    @property
    def formatted(self):
        try:
            # Assume json, and try to format it.
            return self.format_json()
        except ValueError:
            return self.format_html()

    def get_api_response(self, url, headers={}):
        self._request_start = time()
        try:
            response = self.dao.getURL(url, headers)
        except DataFailureException as ex:
            response = MockHTTP()
            response.status = ex.status
            response.data = ex.msg
        self._request_end = time()
        self.response = response
        return self.response

    def format_json(self):
        data = json.loads(self.response.data)
        formatted = json.dumps(data, sort_keys=True, indent=4)
        formatted = formatted.replace("&", "&amp;")
        formatted = formatted.replace("<", "&lt;")
        formatted = formatted.replace(">", "&gt;")
        formatted = formatted.replace(" ", "&nbsp;")
        formatted = formatted.replace("\n", "<br/>\n")

        base_url = reverse("restclients_proxy", args=["xx", "xx"])
        base_url = base_url.replace('/xx/xx', '')

        formatted = re.sub(r"\"/(.*?)\"",
                           r'"<a href="{}/{}/\1">/\1</a>"'.format(
                               base_url, self.service),
                           formatted)
        return formatted

    def format_html(self):
        try:
            content = self.response.data.decode('utf-8')
        except AttributeError:
            content = self.response.data

        base_url = reverse("restclients_proxy", args=["xx", "xx"])
        base_url = base_url.replace('/xx/xx', '')

        formatted = re.sub(r"href\s*=\s*[\"\']/(.*?)[\"\']",
                           r'href="{}/{}/\1"'.format(base_url, self.service),
                           content, flags=re.I)
        formatted = re.sub(
            re.compile(r"<style.*/style>", flags=re.S | re.I), "", formatted)
        formatted = self.clean_self_closing_divs(formatted)
        return formatted

    @staticmethod
    def clean_self_closing_divs(content):
        return re.sub(r"((<div[^>]*?)/>)",
                      r"<!-- \g<1> -->\g<2>></div>",
                      content)


class DegradePerformance(object):
    def __init__(self, serialized=None):
        self.problems = {}

        if serialized:
            self.problems = json.loads(serialized)

    def remove_service(self, service):
        del self.problems[service]

    def set_status(self, service, value):
        self._set(service, "status", value)

    def set_content(self, service, value):
        self._set(service, "content", value)

    def set_load_time(self, service, value):
        self._set(service, "load_time", value)

    def get_status(self, service):
        return self._get(service, "status")

    def get_content(self, service):
        return self._get(service, "content")

    def get_load_time(self, service):
        return self._get(service, "load_time")

    def services(self):
        return self.problems.keys()

    def _set(self, service, key, value):
        self._add_service(service)
        self.problems[service][key] = value

    def _get(self, service, key):
        if service in self.problems:
            if key in self.problems[service]:
                return self.problems[service][key]
        return None

    def _add_service(self, service):
        if service not in self.problems:
            self.problems[service] = {}

    def serialize(self):
        return json.dumps(self.problems)
