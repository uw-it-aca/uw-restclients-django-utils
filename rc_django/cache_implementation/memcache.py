"""
Contains memcached cache implementations
"""

import bmemcached
from bmemcached.exceptions import MemcachedException
import logging
import pickle
import threading
from dateutil.parser import parse
from django.conf import settings
from django.utils import timezone
from restclients_core.models import MockHTTP


logger = logging.getLogger(__name__)


class MemcachedCache(object):

    def __init__(self):
        self._set_client()

    def getCache(self, service, url, headers):
        key = self._get_key(service, url)
        try:
            data = self.client.get(key)
        except MemcachedException as ex:
            logger.error("Get (key: %s) ==> %s", key, str(ex))
            return

        if not data:
            return None

        values = pickle.loads(data)
        response = MockHTTP()
        response.headers = values["headers"]
        response.status = values["status"]
        response.data = values["data"]

        return {"response": response}

    def updateCache(self, service, url, new_data, new_data_dt):
        """
        :param new_data: a string representation of the data
        :param new_data_dt: a timezone aware datetime object giving
                the timestamp of the new_data
        :raise MemcachedException: if update failed
        """
        key = self._get_key(service, url)

        # clear existing data
        try:
            value = self.client.get(key)
            if value:
                data = pickle.loads(value)
                if "time_stamp" in data:
                    cached_data_dt = parse(data["time_stamp"])
                    if new_data_dt > cached_data_dt:
                        self.client.delete(key)
                        # may raise MemcachedException
                        logger.info("IN cache (key: %s), older DELETE", key)
                    else:
                        logger.info("IN cache (key: %s), newer KEEP", key)
                        return
            else:
                logger.info("NOT IN cache (key: %s)", key)

        except MemcachedException as ex:
            logger.error("Clear existing data (key: %s) ==> %s", key, str(ex))
            return

        # store new value in cache
        cdata, time_to_store = self._make_cache_data(
            service, url, new_data, {}, 200, new_data_dt)

        self.client.set(key, cdata, time=time_to_store)
        # may raise MemcachedException
        logger.info("MemCached SET (key %s) for %d seconds",
                    key, time_to_store)

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
        cdata, time_to_store = self._make_cache_data(service, url,
                                                     response.data,
                                                     header_data,
                                                     response.status,
                                                     timezone.now())
        try:
            self.client.set(key, cdata, time=time_to_store)
            logger.info("MemCached set with key '%s', %d seconds",
                        key, time_to_store)
        except bmemcached.exceptions.MemcachedException as ex:
            logger.error("set (key: %s) ==> %s", key, str(ex))
        return

    def get_cache_expiration_time(self, service, url):
        # Over-ride this to define your own.
        return 60 * 60 * 4

    def _get_key(self, service, url):
        return "%s-%s" % (service, url)

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

        self.client = bmemcached.Client(servers, username, password)
        MemcachedCache._memcached_cache[thread_id] = self.client
