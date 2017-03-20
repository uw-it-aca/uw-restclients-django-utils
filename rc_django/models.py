from django.db import models
from base64 import b64encode, b64decode
import pickle


class CacheEntry(models.Model):
    service = models.CharField(max_length=50, db_index=True)
    url = models.CharField(max_length=255, unique=True, db_index=True)
    status = models.PositiveIntegerField()
    header_pickle = models.TextField()
    content = models.TextField()
    headers = None

    class Meta:
        db_table = 'restclients_cacheentry'
        unique_together = ('service', 'url')

    def getHeaders(self):
        if self.headers is None:
            if self.header_pickle is None:
                self.headers = {}
            else:
                self.headers = pickle.loads(b64decode(self.header_pickle))
        return self.headers

    def setHeaders(self, headers):
        self.headers = headers

    def save(self, *args, **kwargs):
        pickle_content = ""
        if self.headers:
            pickle_content = pickle.dumps(self.headers)
        else:
            pickle_content = pickle.dumps({})

        self.header_pickle = b64encode(pickle_content)
        super(CacheEntry, self).save(*args, **kwargs)


class CacheEntryTimedManager(models.Manager):
    def find_nonexpired_by_service_and_url(self, service, url, time_limit):
        return super(CacheEntryTimedManager, self).get_queryset().filter(
            service=service, url=url, time_saved__gte=time_limit)

    def find_by_service_and_url(self, service, url):
        return super(CacheEntryTimedManager, self).get_queryset().filter(
            service=service, url=url)


class CacheEntryTimed(CacheEntry):
    time_saved = models.DateTimeField()

    objects = CacheEntryTimedManager()

    class Meta:
        db_table = 'restclients_cacheentrytimed'
