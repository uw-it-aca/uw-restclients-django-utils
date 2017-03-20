from django.test import TestCase
from restclients_core.dao import DAO, MockDAO
from restclients_core.models import MockHTTP
from rc_django.cache_implementation import ETagCache


class ETAG_DAO(DAO):
    def service_name(self):
        return "etag"

    def get_default_service_setting(self, key):
        if "DAO_CLASS" == key:
            return "rc_django.tests.cache_implementation.test_etag.ETag"

    def get_cache(self):
        return ETagCache()


class ETag(MockDAO):
    def load(self, method, url, headers, body):
        response = MockHTTP()
        if "If-None-Match" in headers and url == "/same":
            response.status = 304
        else:
            response.status = 200
            response.data = "Body Content"
            response.headers = {"ETag": "A123BBB"}
        return response


class ETagCacheTest(TestCase):
    def test_etags(self):
        # Check initial state
        cache = ETagCache()
        response = cache.getCache('etag', '/same', {})
        self.assertEquals(response, None)

        etag = ETAG_DAO()
        initial_response = etag.getURL('/same', {})

        content = initial_response.data

        # Make sure there's a response there after the get
        headers = {}
        hit = cache.getCache('etag', '/same', headers)

        self.assertEquals(hit, None)

        if_match = headers.get("If-None-Match")

        self.assertEquals(if_match, "A123BBB")

        mock_304 = MockHTTP()
        mock_304.status = 304
        hit = cache.processResponse('etag', '/same', mock_304)
        response = hit["response"]

        self.assertEquals(response.status, 200)
        self.assertEquals(response.data, content)

        # Make sure there's nothing there after the get
        response = cache.getCache('etag', '/same', {})
        self.assertEquals(response, None)
