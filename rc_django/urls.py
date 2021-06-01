# Copyright 2021 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.urls import re_path
from rc_django.views.errors import DegradePerformanceView
from rc_django.views.rest_proxy import RestSearchView, RestProxyView

urlpatterns = [
    re_path(r'^errors',
            DegradePerformanceView.as_view(), name="restclients_errors"),
    re_path(r'^search/(\w+)/(.*)$',
            RestSearchView.as_view(), name="restclients_customform"),
    re_path(r'^view/(\w+)/(.*)$',
            RestProxyView.as_view(), name="restclients_proxy"),
]
