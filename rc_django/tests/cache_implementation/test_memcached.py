import json
from django.test import TestCase
from django.utils import timezone
from rc_django.cache_implementation.memcache import MemcachedCache


class MClient():

    cache = {}

    def delete(self, key):
        if key in MClient.cache:
            del MClient.cache[key]

    def get(self, key):
        if key in MClient.cache:
            return MClient.cache[key]
        return None

    def set(self, key, cdata, time=None):
        if key not in MClient.cache:
            MClient.cache[key] = cdata


class TestCache(MemcachedCache):

    def __init__(self):
        super(TestCache, self).__init__()

    def _set_client(self):
        self.client = MClient()

    def make_cache_data(self):
        return self._make_cache_data(
            'mem', '/same', json.dumps({"data": "Body Content"}),
            {}, 200, timezone.now())


class MemcachedCacheTest(TestCase):

    def test_cacheGet(self):
        cache = TestCache()
        key = cache._get_key('mem', '/same')
        self.assertEquals(key, "mem-/same")

        data = cache.getCache('mem', '/same', {})
        self.assertIsNone(data)

        cdata, time_to_store = cache.make_cache_data()
        cache.client.set(key, cdata, time_to_store)

        hit = cache.getCache('mem', '/same', {})
        response = hit["response"]
        self.assertEquals(response.status, 200)
        self.assertEquals(response.data, '{"data": "Body Content"}')

    def test_updateCache(self):
        cache = TestCache()
        cache.updateCache('mem', '/same',
                          '{"data": "Body Content"}',
                          timezone.now())

        hit = cache.getCache('mem', '/same', {})
        response = hit["response"]
        self.assertEquals(response.headers, {})
        self.assertEquals(response.status, 200)
        self.assertEquals(response.data, '{"data": "Body Content"}')
