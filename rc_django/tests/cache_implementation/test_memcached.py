import json
from django.test import TestCase
from django.conf import settings
from django.utils import timezone
from restclients_core.dao import DAO, MockDAO
from restclients_core.models import MockHTTP
from rc_django.cache_implementation.memcache import MemcachedCache
from unittest import skipIf


MEMCACHE = 'rc_django.cache_implementation.memcache.MemcachedCache'


class MEM_DAO(DAO):
    def service_name(self):
        return "mem"

    def get_default_service_setting(self, key):
        if "DAO_CLASS" == key:
            return (
                "rc_django.tests.cache_implementation.test_memcached.Backend")

    def get_cache(self):
        return MemcachedCache()


class Backend(MockDAO):
    def load(self, method, url, headers, body):
        response = MockHTTP()
        if url == "/same":
            response.status = 200
            response.data = "Body Content"
        else:
            response.status = 404
        return response


@skipIf(not getattr(settings, 'RESTCLIENTS_TEST_MEMCACHED', False),
        "Memcached cache backend not configured")
class MemcachedCacheTest(TestCase):
    def setUp(self):
        cache = MemcachedCache()
        cache.client.flush_all()

    def test_memcached(self):
        cache = MemcachedCache()
        client = MEM_DAO()
        client.getURL('/same', {})

        hit = cache.getCache('mem', '/same', {})
        response = hit["response"]

        self.assertEquals(response.status, 200)
        self.assertEquals(response.data, "Body Content")

        hit = cache.getCache('mem', '/same', {})

        self.assertEquals(response.status, 200)
        self.assertEquals(response.data, "Body Content")

    def test_memcached_404(self):
        cache = MemcachedCache()
        client = MEM_DAO()
        client.getURL('/asd', {})

        hit = cache.getCache('mem', '/asd', {})
        response = hit["response"]
        self.assertEquals(response.status, 404)

        hit = cache.getCache('mem', '/asd', {})
        self.assertEquals(response.status, 404)

    def test_longkeys(self):
        cache = MemcachedCache()
        url = "".join("X" for i in range(300))

        ok_response = MockHTTP()
        ok_response.status = 200
        ok_response.data = "valid"
        cache.processResponse('ok', url, ok_response)

        # This makes sure we don't actually cache anything when the url
        # is too long
        response = cache.getCache('ok', url, {})
        self.assertEquals(response, None)

        # But the get doesn't raise the exception w/ the set before it,
        # so this redundant-looking code is testing to make sure that we
        # catch the exception on the get as well.
        url = "".join("Y" for i in range(300))
        response = cache.getCache('ok', url, {})
        self.assertEquals(response, None)

    def test_updateCache(self):
        cache = MemcachedCache()
        ret = cache.getCache('mem', '/update', {})
        self.assertIsNone(ret)

        updates = [{"Color": "red"}, {"Color": "blue"}, {"Color": None}]

        for update in updates:
            cache.updateCache(
                'mem', '/update', json.dumps(update), timezone.now())

            ret = cache.getCache('mem', '/update', {})
            response = ret["response"]
            self.assertEquals(response.status, 200)
            self.assertEquals(json.loads(response.data), update)
