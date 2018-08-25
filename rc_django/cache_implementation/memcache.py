"""
Contains memcached cache implementations
"""

from base64 import b64encode, b64decode
import bmemcached
from bmemcached.exceptions import MemcachedException
import json
import logging
import threading
from django.conf import settings
from django.utils import timezone
from dateutil.parser import parse
from restclients_core.models import MockHTTP


logger = logging.getLogger(__name__)


class MemcachedCache(object):

    def getCache(self, service, url, headers):
        client = self._get_client()
        key = self._get_key(service, url)
        try:
            data = client.get(key)
        except MemcachedException as ex:
            logger.error("Get (key: %s) ==> %s", key, str(ex))
            return

        if not data:
            return

        values = json.loads(data)
        if "b64_data" in data:
            values["data"] = b64decode(values["b64_data"])
        response = MockHTTP()
        response.status = values["status"]
        response.data = values["data"]
        response.headers = values["headers"]

        return {"response": response}

    def updateCache(self, service, url, new_data, new_data_dt):
        """
        :param new_data: a string representation of the data
        :param new_data_dt: a timezone aware datetime object
        :raise MemcachedException: if update failed
        """
        client = self._get_client()
        key = self._get_key(service, url)

        # clear existing data
        try:
            value = client.get(key)
            if value:
                data = json.loads(value)
                if "time_stamp" in data:
                    cached_data_dt = parse(data["time_stamp"])
                    if new_data_dt > cached_data_dt:
                        client.delete(key)
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
        cdata, time_to_store = self.__make_cache_data(
            service, url, new_data, {}, 200, new_data_dt)

        client.set(key, cdata, time=time_to_store)
        # may raise MemcachedException
        logger.info("MemCached SET (key %s) for %d seconds",
                    key, time_to_store)

    def __make_cache_data(self, service, url, value_str,
                          header_data, status, time_stamp):
        b64_data = b64encode(value_str)
        data = json.dumps({"status": status,
                           "b64_data": b64_data,
                           "headers": header_data,
                           "time_stamp": str(time_stamp)})
        time_to_store = self.get_cache_expiration_time(service, url)
        return data, time_to_store

    def processResponse(self, service, url, response):
        header_data = {}
        for header in response.headers:
            header_data[header] = response.getheader(header)

        key = self._get_key(service, url)
        cdata, time_to_store = self.__make_cache_data(service, url,
                                                      response.data,
                                                      header_data,
                                                      response.status,
                                                      timezone.now())
        client = self._get_client()
        try:
            client.set(key, cdata, time=time_to_store)
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

    def _get_client(self):
        thread_id = threading.current_thread().ident
        if not hasattr(MemcachedCache, "_memcached_cache"):
            MemcachedCache._memcached_cache = {}

        if thread_id in MemcachedCache._memcached_cache:
            return MemcachedCache._memcached_cache[thread_id]

        servers = settings.RESTCLIENTS_MEMCACHED_SERVERS
        username = getattr(settings, "RESTCLIENTS_MEMCACHED_USER", None)
        password = getattr(settings, "RESTCLIENTS_MEMCACHED_PASS", None)

        client = bmemcached.Client(servers, username, password)

        MemcachedCache._memcached_cache[thread_id] = client

        return client
