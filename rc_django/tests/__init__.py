# Copyright 2021 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

def can_proxy_restclient(request, service, url):
    if service:
        return service in ['test', 'fake']
    return True
