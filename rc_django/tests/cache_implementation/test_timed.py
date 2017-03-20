from django.test import TestCase
from restclients_core.dao import DAO, MockDAO
from restclients_core.models import MockHTTP
from rc_django.cache_implementation import TimeSimpleCache, FourHourCache
from rc_django.models import CacheEntryTimed
from datetime import timedelta


class TIMED_DAO(DAO):
    def service_name(self):
        return "timed"

    def get_default_service_setting(self, key):
        if "DAO_CLASS" == key:
            return "rc_django.tests.cache_implementation.test_timed.Backend"


class SIMPLE_DAO(TIMED_DAO):
    def service_name(self):
        return "simple"

    def get_cache(self):
        return TimeSimpleCache()


class FOUR_DAO(TIMED_DAO):
    def service_name(self):
        return "four"

    def get_cache(self):
        return FourHourCache()


class Backend(MockDAO):
    def load(self, method, url, headers, body):
        response = MockHTTP()
        if url == "/same":
            response.status = 200
            response.data = "Body Content"
        else:
            response.status = 404
        return response


class TimeCacheTest(TestCase):
    def test_saved_headers(self):
        cache = TimeSimpleCache()

        response = MockHTTP()
        response.status = 200
        response.data = "Cache testing"
        response.headers = {
            "link": "next,http://somewhere",
            "Content-type": "text",
            "random": "stuff",
            "and": "more",
        }

        cache._process_response("cache_test", "/v1/headers", response)

        from_db = cache._response_from_cache(
            "cache_test", "/v1/headers", {}, 10)

        self.assertEquals(from_db["response"].status, 200)
        self.assertEquals(from_db["response"].data, "Cache testing")
        self.assertEquals(from_db["response"].getheader("random"), "stuff")
        self.assertEquals(from_db["response"].getheader("and"), "more")
        self.assertEquals(
            from_db["response"].getheader("Content-type"), "text")
        self.assertEquals(
            from_db["response"].getheader("link"), "next,http://somewhere")

    def test_simple_cache(self):
        # Check initial state
        cache = TimeSimpleCache()
        response = cache.getCache('simple', '/same', {})
        self.assertEquals(response, None)

        client = SIMPLE_DAO()
        response = client.getURL('/same', {})

        self.assertEquals(response.status, 200)
        self.assertEquals(response.data, "Body Content")

        # Make sure there's a response there after the get
        hit = cache.getCache('simple', '/same', {})
        response = hit["response"]

        self.assertEquals(response.status, 200)
        self.assertEquals(response.data, "Body Content")

    def test_4hour_cache(self):
        # Check initial state
        cache = FourHourCache()
        response = cache.getCache('four', '/same', {})
        self.assertEquals(response, None)

        client = FOUR_DAO()
        response = client.getURL('/same', {})

        self.assertEquals(response.data, "Body Content")

        # Make sure there's a response there after the get
        hit = cache.getCache('four', '/same', {})
        response = hit["response"]

        self.assertEquals(response.status, 200)
        self.assertEquals(response.data, "Body Content")

        cache_entry = CacheEntryTimed.objects.get(service="four", url="/same")

        # Cached response is returned after 3 hours and 58 minutes
        orig_time_saved = cache_entry.time_saved
        cache_entry.time_saved = orig_time_saved - timedelta(minutes=238)
        cache_entry.save()

        hit = cache.getCache('four', '/same', {})
        self.assertNotEquals(hit, None)

        # Cached response is not returned after 4 hours and 1 minute
        cache_entry.time_saved = orig_time_saved - timedelta(hours=241)
        cache_entry.save()

        hit = cache.getCache('four', '/same', {})
        self.assertEquals(hit, None)

    def test_errors(self):
        cache = FourHourCache()
        response = cache.getCache('four', '/invalid', {})
        self.assertEquals(response, None)

        client = FOUR_DAO()
        response = client.getURL('/invalid', {})

        hit = cache.getCache('four', '/invalid', {})
        response = hit["response"]

        self.assertEquals(response.status, 404)

        cache_entry = CacheEntryTimed.objects.get(
            service="four", url="/invalid")

        # Make sure that invalid entry stops being returned after 5 mintes
        cache_entry.time_saved = cache_entry.time_saved - timedelta(minutes=5)
        cache_entry.save()

        hit = cache.getCache('four', '/invalid', {})
        self.assertEquals(hit, None, "No hit on old, bad status codes")

        # Make sure bad responses don't overwrite good ones.
        ok_response = MockHTTP()
        ok_response.status = 200
        ok_response.data = "OK"

        cache.processResponse("four", "/ok", ok_response)

        cache_response = cache.getCache("four", "/ok", {})
        response = cache_response["response"]
        self.assertEquals(response.status, 200)

        bad_response = MockHTTP()
        bad_response.status = 500
        bad_response.data = "This is bad data"

        cache.processResponse("four", "/ok", bad_response)
        cache_response = cache.getCache("four", "/ok", {})
        response = cache_response["response"]
        self.assertEquals(response.status, 200)
        self.assertEquals(response.data, "OK")

        # Make sure that an old, good hit is returned when there's a fresh,
        # bad hit.
        ok_response = MockHTTP()
        ok_response.status = 200
        ok_response.data = "Valid"

        cache.processResponse("four", "/valid", ok_response)

        response = client.getURL("/valid", {})
        self.assertEquals(response.status, 200)

        cache_entry = CacheEntryTimed.objects.get(
            service="four", url="/valid")

        cache_entry.time_saved = cache_entry.time_saved - timedelta(hours=5)
        cache_entry.save()

        response = client.getURL("/valid", {})
        self.assertEquals(response.status, 200)

        # But make sure eventually we stop using our cache.
        cache_entry.time_saved = cache_entry.time_saved - timedelta(hours=9)
        cache_entry.save()

        response = client.getURL("/valid", {})
        self.assertEquals(response.status, 404)
