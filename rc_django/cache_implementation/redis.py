"""
Contains redis cache implementations
"""
import redis
import redis.exceptions.RedisError
import logging
import pickle
import threading
from dateutil.parser import parse
from django.conf import settings
from django.utils import timezone
from restclients_core.models import MockHTTP


logger = logging.getLogger(__name__)


class RedisCache(object):

    def __init__(self):
        self._set_client()

    def getCache(self, service, url, headers):
        keyV = self._get_key(service, url)
        try:
            data = self.client.get(key)
        except RedisError as ex:
            logger.error("Get (key: {}) ==> {}".format(key, str(ex)))
            return

        if not data:
            return None

        values = pickle.loads(data, encoding="utf8")
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
        :raise RedisError: if update failed
        """
        key = self._get_key(service, url)

        # clear existing data
        try:
            value = self.client.get(key)
            if value:
                data = pickle.loads(value, encoding="utf8")
                if "time_stamp" in data:
                    cached_data_dt = parse(data["time_stamp"])
                    if new_data_dt > cached_data_dt:
                        self.client.delete(key)
                        # may raise RedisError
                        logger.info(
                            "IN cache (key: {}), older DELETE".format(key))
                    else:
                        logger.info(
                            "IN cache (key: {}), newer KEEP".format(key))
                        return
            else:
                logger.info("NOT IN cache (key: {})".format(key))

        except RedisError as ex:
            logger.error(
                "Clear existing data (key: {}) ==> {}".format(key, str(ex)))
            return

        # store new value in cache
        cdata, time_to_store = self._make_cache_data(
            service, url, new_data, {}, 200, new_data_dt)

        self.client.set(key, cdata, ex=time_to_store)
        # may raise RedisError
        logger.info(
            "Redis SET (key {}) for {:d} seconds".format(
                key, time_to_store))

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
            self.client.set(key, cdata, ex=time_to_store)
            logger.info("Redis set with key '{}', {:d} seconds".format(
                key, time_to_store))
        except RedisError as ex:
            logger.error("set (key: {}) ==> {}".format(key, str(ex)))
        return

    def get_cache_expiration_time(self, service, url):
        # Over-ride this to define your own.
        return 60 * 60 * 4

    def _get_key(self, service, url):
        return "{}-{}".format(service, url)

    def _set_client(self):
        thread_id = threading.current_thread().ident
        if not hasattr(RedisCache, "_redis_cache"):
            RedisCache._redis_cache = {}

        if thread_id in RedisCache._redis_cache:
            self.client = RedisCache._redis_cache[thread_id]
            return

        endpoint = settings.RESTCLIENTS_REDIS_ENDPOINT

        username = getattr(settings, "RESTCLIENTS_REDIS_USER", None)
        password = getattr(settings, "RESTCLIENTS_REDIS_PASS", None)

        self.client = redis.Redis(host=endpoint, username=username,
                                  password=password)
