from django.test import TestCase, RequestFactory
from django.test.utils import override_settings
from django.urls import reverse
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.middleware import AuthenticationMiddleware
from django.contrib.auth.models import User
from userservice.user import UserServiceMiddleware
from restclients_core.dao import DAO, MockDAO
from restclients_core.models import MockHTTP
from rc_django.views import errors
from rc_django.middleware import EnableServiceDegradationMiddleware
from rc_django.tests.test_views import missing_url
import time


class DELAY_DAO(DAO):
    def service_name(self):
        return "delay"

    def get_default_service_setting(self, key):
        if "DAO_CLASS" == key:
            return "rc_django.tests.performance.test_delay.Backend"


class Backend(MockDAO):
    def load(self, method, url, headers, body):
        response = MockHTTP()
        response.status = 200
        response.data = "ok"
        return response


class DegradedTestCase(TestCase):

    @override_settings(
        RESTCLIENTS_ADMIN_AUTH_MODULE='rc_django.tests.can_proxy_restclient')
    def test_degraded(self):
        r1 = RequestFactory().post(reverse("restclients_errors"), {
            "new_service_name": "delay",
            "new_service_status": 500,
            "new_service_content": "[oops",
            "new_service_load_time": 0.1,
        })
        r2 = RequestFactory().get("/")

        SessionMiddleware().process_request(r1)
        SessionMiddleware().process_request(r2)

        AuthenticationMiddleware().process_request(r1)
        UserServiceMiddleware().process_request(r1)

        AuthenticationMiddleware().process_request(r2)
        UserServiceMiddleware().process_request(r2)

        user = User.objects.create_user(username='delay_user',
                                        email='fake2@fake',
                                        password='top_secret')

        r1.user = user
        r2.user = user

        r1._dont_enforce_csrf_checks = True

        errors(r1)

        r1.session.save()

        EnableServiceDegradationMiddleware().process_request(r1)

        client = DELAY_DAO()
        t1 = time.time()
        response = client.getURL("/test", {})
        t2 = time.time()
        self.assertEquals(response.status, 500)
        self.assertEquals(response.data, "[oops")

        self.assertGreater(t2-t1, 0.09)

        EnableServiceDegradationMiddleware().process_request(r2)

        response = client.getURL("/test", {})
        self.assertEquals(response.status, 200)
