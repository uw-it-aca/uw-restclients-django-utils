import json
from django.db import models
from hashlib import sha1


class CacheEntry(models.Model):
    service = models.CharField(max_length=50, db_index=True)
    url = models.TextField()
    url_key = models.SlugField(max_length=40, unique=True)
    status = models.PositiveIntegerField()
    content = models.TextField()
    headers = models.TextField()

    class Meta:
        app_label = 'rc_django'
        db_table = 'restclients_cacheentry'
        unique_together = ('service', 'url_key')

    def getHeaders(self):
        return json.loads(self.headers)

    def save(self, *args, **kwargs):
        self.headers = json.dumps(self.headers)
        self.url_key = self.get_url_key(self.url)
        super(CacheEntry, self).save(*args, **kwargs)

    @staticmethod
    def get_url_key(url):
        return sha1(url.encode('utf-8')).hexdigest()


class CacheEntryTimedManager(models.Manager):
    def find_nonexpired_by_service_and_url(self, service, url, time_limit):
        return super(CacheEntryTimedManager, self).get_queryset().filter(
            service=service, url_key=CacheEntry.get_url_key(url),
            time_saved__gte=time_limit)

    def find_by_service_and_url(self, service, url):
        return super(CacheEntryTimedManager, self).get_queryset().filter(
            service=service, url_key=CacheEntry.get_url_key(url))


class CacheEntryTimed(CacheEntry):
    time_saved = models.DateTimeField()

    objects = CacheEntryTimedManager()

    class Meta:
        app_label = 'rc_django'
        db_table = 'restclients_cacheentrytimed'


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
