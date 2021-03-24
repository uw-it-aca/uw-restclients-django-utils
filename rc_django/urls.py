# Copyright 2021 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.conf.urls import url
from rc_django.views import proxy, errors


urlpatterns = [
    url(r'errors', errors, name="restclients_errors"),
    url(r'view/(\w+)/(.*)$', proxy, name="restclients_proxy"),
]
