"""
Contains memcached cache implementations
"""

from bmemcached import Client
from bmemcached.exceptions import MemcachedException
import logging
import pickle
import threading
from dateutil.parser import parse
from django.conf import settings
from django.utils import timezone
from restclients_core.models import MockHTTP
from rc_django.cache_implementation.logger import log_err, log_info


logger = logging.getLogger(__name__)


class MemcachedCache(object):

    def __init__(self):
        self._set_client()

    def deleteCache(self, service, url):
        key = self._get_key(service, url)
        try:
            return self.client.delete(key)
        except MemcachedException as ex:
            log_err(logger, "MemCache Delete(key: {}) => {}".format(key, ex))

    def getCache(self, service, url, headers):
        expire_seconds = self.get_cache_expiration_time(service, url)
        if expire_seconds is None:
            return

        key = self._get_key(service, url)
        try:
            data = self.client.get(key)
        except MemcachedException as ex:
            log_err(logger, "MemCache Get(key: {}) => {}".format(key, ex))
            return

        if not data:
            return

        values = self._get_cache_data(data)
        response = MockHTTP()
        response.headers = values["headers"]
        response.status = values["status"]
        response.data = values["data"]

        return {"response": response}

    def processResponse(self, service, url, response):
        expire_seconds = self.get_cache_expiration_time(service, url)
        if expire_seconds is None:
            return

        header_data = {}
        for header in response.headers:
            header_data[header] = response.getheader(header)

        key = self._get_key(service, url)
        cdata = self._make_cache_data(
            service, url, response.data, header_data, response.status,
            timezone.now())
        try:
            self.client.set(key, cdata, time=expire_seconds)
            log_info(logger, "MemCache Set(key: {})".format(key))
        except MemcachedException as ex:
            log_err(logger, "MemCache Set(key: {}) => {}".format(key, ex))

    def updateCache(self, service, url, new_data, new_data_dt):
        """
        :param new_data: a string representation of the data
        :param new_data_dt: a timezone aware datetime object giving
                the timestamp of the new_data
        :raise MemcachedException: if update failed
        """
        expire_seconds = self.get_cache_expiration_time(service, url)
        if expire_seconds is None:
            return

        key = self._get_key(service, url)
        cdata = self._make_cache_data(
            service, url, new_data, {}, 200, new_data_dt)
        try:
            value = self.client.get(key)
            if value:
                data = self._get_cache_data(value)
                if "time_stamp" in data:
                    cached_data_dt = parse(data["time_stamp"])
                    if new_data_dt <= cached_data_dt:
                        log_info(logger, "IN cache (key: {})".format(key))
                        return
                # replace existing value in cache
                self.client.replace(key, cdata, time=expire_seconds)
                log_info(logger, "MemCache replace(key: {})".format(key))
                return
        except MemcachedException as ex:
            log_err(logger, "MemCache replace(key: {}) => {}".format(key, ex))
            raise

        # not in cache
        try:
            self.client.set(key, cdata, time=expire_seconds)
            log_info(logger, "MemCache Set(key {})".format(key))
        except MemcachedException as ex:
            log_err(logger, "MemCache Set(key: {}) => {}".format(key, ex))
            raise

    def _get_cache_data(self, data_from_cache):
        return pickle.loads(data_from_cache, encoding="utf8")

    def _make_cache_data(self, service, url, data_to_cache,
                         header_data, status, time_stamp):
        return pickle.dumps({
            "status": status,
            "headers": header_data,
            "data": data_to_cache,
            "time_stamp": time_stamp.isoformat(),
        })

    """
    Returns an integer representing seconds until a document expires,
    overridden to set per-URL expiration times.  The default is 4 hours.

    Following memcached documentation:
      # Can be set from 0, meaning "never expire", to 30 days (60*60*24*30).
      # Any time higher than 30 days is interpreted as a unix timestamp date.

    A value of None indicates "Do not cache", and will not use the cache.
    """
    def get_cache_expiration_time(self, service, url):
        return 60 * 60 * 4

    def _get_key(self, service, url):
        return "{}-{}".format(service, url)

    def _set_client(self):
        thread_id = threading.current_thread().ident
        if not hasattr(MemcachedCache, "_memcached_cache"):
            MemcachedCache._memcached_cache = {}

        if thread_id in MemcachedCache._memcached_cache:
            self.client = MemcachedCache._memcached_cache[thread_id]
            return

        servers = settings.RESTCLIENTS_MEMCACHED_SERVERS
        username = getattr(settings, "RESTCLIENTS_MEMCACHED_USER", None)
        password = getattr(settings, "RESTCLIENTS_MEMCACHED_PASS", None)

        self.client = Client(servers, username, password)
        MemcachedCache._memcached_cache[thread_id] = self.client
