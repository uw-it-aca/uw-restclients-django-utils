import json
from unittest import skipIf
from django.conf import settings
from django.test import TestCase
from django.utils import timezone
from restclients_core.models import MockHTTP
from rc_django.cache_implementation.memcache import MemcachedCache


@skipIf(not getattr(settings, 'RESTCLIENTS_MEMCACHED_SERVERS', None),
        "Memcached cache not configured")
class MemcachedCacheTest(TestCase):
    def setUp(self):
        cache = MemcachedCache()
        cache.client.flush_all()

    def test_cacheGet(self):
        cache = MemcachedCache()
        key = cache._get_key('mem', '/same')
        self.assertEquals(key, "mem-/same")

        data = cache.getCache('mem', '/same', {})
        self.assertIsNone(data)

        cdata, time_to_store = cache._make_cache_data(
            'mem', '/same', json.dumps({"data": "Body Content"}),
            {}, 200, timezone.now())
        cache.client.set(key, cdata, time_to_store)

        hit = cache.getCache('mem', '/same', {})
        response = hit["response"]
        self.assertEquals(response.status, 200)
        self.assertEquals(response.data, '{"data": "Body Content"}')

    def test_updateCache(self):
        cache = MemcachedCache()
        # cache no data
        cache.updateCache('mem', '/same', '{"data": "Content1"}',
                          timezone.now())

        time1 = timezone.now()
        # cache has older data
        cache.updateCache('mem', '/same', '{"data": "Content2"}', time1)

        hit = cache.getCache('mem', '/same', {})
        response = hit["response"]
        self.assertEquals(response.headers, {})
        self.assertEquals(response.status, 200)
        self.assertEquals(response.data, '{"data": "Content2"}')

        # update with no newer data
        cache.updateCache('mem', '/same', '{"data": "Content3"}', time1)
        hit = cache.getCache('mem', '/same', {})
        response = hit["response"]
        self.assertEquals(response.data, '{"data": "Content2"}')

    def test_processResponse(self):
        mock_resp = MockHTTP()
        mock_resp.status = 200
        mock_resp.data = "Content4"
        mock_resp.headers = {"Content-type": "text/html"}

        cache = MemcachedCache()
        cache.processResponse('mem', '/same1', mock_resp)

        hit = cache.getCache('mem', '/same1', {})
        response = hit["response"]
        self.assertEquals(response.headers, {"Content-type": "text/html"})
        self.assertEquals(response.status, 200)
        self.assertEquals(response.data, "Content4")

    def test_binary_processResponse(self):
        mock_resp = MockHTTP()
        mock_resp.status = 200
        mock_resp.data = b'content to be encoded'
        mock_resp.headers = {"Content-type": "image/png"}

        cache = MemcachedCache()
        cache.processResponse('mem', '/same2', mock_resp)

        hit = cache.getCache('mem', '/same2', {})
        response = hit["response"]
        self.assertEquals(response.headers, {"Content-type": "image/png"})
        self.assertEquals(response.status, 200)
        self.assertEquals(response.data, b'content to be encoded')

    def test_memcached_client(self):
        cache = MemcachedCache()
        key = cache._get_key('mem', '/same')
        self.assertEquals(key, "mem-/same")
        cache.updateCache('mem', '/same', '{"data": "Content"}',
                          timezone.now())
        hit = cache.getCache('mem', '/same', {})
        response = hit["response"]
        self.assertEquals(response.headers, {})
        self.assertEquals(response.status, 200)
