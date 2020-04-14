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
from rc_django.cache_implementation.logger import log_err


logger = logging.getLogger(__name__)


class MemcachedCache(object):

    def __init__(self):
        self._set_client()

    def getCache(self, service, url, headers):
        key = self._get_key(service, url)
        try:
            data = self.client.get(key)
        except MemcachedException as ex:
            log_err(logger, "MemCached Get(key: {}) => {}".format(key, ex))
            return None

        if not data:
            return None

        values = pickle.loads(data, encoding="utf8")
        response = MockHTTP()
        response.headers = values["headers"]
        response.status = values["status"]
        response.data = values["data"]

        return {"response": response}

    def deleteCache(self, service, url):
        key = self._get_key(service, url)
        try:
            return self.client.delete(key)
        except MemcachedException as ex:
            log_err(logger, "MemCached Delete(key: {}) => {}".format(key, ex))
            return False

    def updateCache(self, service, url, new_data, new_data_dt):
        """
        :param new_data: a string representation of the data
        :param new_data_dt: a timezone aware datetime object giving
                the timestamp of the new_data
        """
        key = self._get_key(service, url)
        cdata, time_to_store = self._make_cache_data(
            service, url, new_data, {}, 200, new_data_dt)
        try:
            value = self.client.get(key)
        except MemcachedException as ex:
            log_err(logger, "MemCached Get(key: {}) => {}".format(key, ex))
            return

        if value is None:
            # not in cache
            try:
                self.client.set(key, cdata, time=time_to_store)
                logger.debug("MemCached SET (key {}) for {:d} seconds".format(
                    key, time_to_store))
            except MemcachedException as ex:
                log_err(logger, "MemCached Set(key: {}) => {}".format(key, ex))
            return

        data = pickle.loads(value, encoding="utf8")
        if "time_stamp" in data:
            cached_data_dt = parse(data["time_stamp"])
            if new_data_dt <= cached_data_dt:
                logger.debug("IN cache (key: {}), KEEP".format(key))
                return
        # replace existing value in cache
        try:
            self.client.replace(key, cdata, time=time_to_store)
            logger.debug("IN cache (key: {}), REPLACE".format(key))
        except MemcachedException as ex:
            log_err(logger, "MemCached Replace(key: {}) => {}".format(key, ex))

    def _make_cache_data(self, service, url, data_to_cache,
                         header_data, status, time_stamp):
        data = {"status": status,
                "headers": header_data,
                "data": data_to_cache,
                "time_stamp": time_stamp.isoformat()
                }
        time_to_store = self.get_cache_expiration_time(service, url)
        return pickle.dumps(data), time_to_store

    def processResponse(self, service, url, response):
        header_data = {}
        for header in response.headers:
            header_data[header] = response.getheader(header)

        key = self._get_key(service, url)
        cdata, time_to_store = self._make_cache_data(
            service, url, response.data, header_data,
            response.status, timezone.now())
        try:
            self.client.set(key, cdata, time=time_to_store)
            logger.debug("MemCached set with key '{}', {:d} seconds".format(
                key, time_to_store))
        except MemcachedException as ex:
            log_err(logger, "set (key: {}) ==> {}".format(key, ex))
        return

    def get_cache_expiration_time(self, service, url):
        # Over-ride this to define your own.
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
