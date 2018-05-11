def can_proxy_restclient(request, service, url):
    if service:
        return service in ['test', 'fake']
    return True
