# -*- coding: utf-8 -*-
from django.test import TestCase, RequestFactory
from django.conf import settings
from django.contrib.auth.middleware import AuthenticationMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from restclients_core.dao import DAO, MockDAO
from restclients_core.models import MockHTTP
from rc_django.views import proxy, clean_self_closing_divs, get_class, SERVICES
from userservice.user import UserServiceMiddleware
from unittest import skipIf
import os


class TEST_DAO(DAO):
    def service_name(self):
        return "test"

    def get_default_service_setting(self, key):
        if "DAO_CLASS" == key:
            return "rc_django.tests.test_views.Backend"


class Backend(MockDAO):
    def load(self, method, url, headers, body):
        response = MockHTTP()
        response.status = 200
        response.data = "ok"
        return response


def missing_url(name, *args, **kwargs):
    try:
        url = reverse(name, *args, **kwargs)
    except Exception as ex:
        print("%s" % ex)
        if getattr(settings, "RESTCLIENTS_REQUIRE_VIEW_TESTS", False):
            raise
        return True

    return False


def get_user(username):
    try:
        user = User.objects.get(username=username)
        return user
    except Exception as ex:
        user = User.objects.create_user(username, password='pass')
        return user


def get_user_pass(username):
    return 'pass'


class ViewTest(TestCase):
    def test_simple(self):
        self_closed = "<div/>"
        valid = "<!-- <div/> --><div></div>"

        self.assertEquals(valid, clean_self_closing_divs(self_closed))

    def test_2_simple(self):
        self_closed = "<div/><div/>"
        valid = "<!-- <div/> --><div></div><!-- <div/> --><div></div>"

        self.assertEquals(valid, clean_self_closing_divs(self_closed))

    def test_valid_div(self):
        valid = "<div id='test id'></div>"
        self.assertEquals(valid, clean_self_closing_divs(valid))

    def test_div_then_valid_self_closing(self):
        valid = "<div id='test id'></div><br/>"
        self.assertEquals(valid, clean_self_closing_divs(valid))

    def test_bad_url(self):
        # Something was sending urls that should have been
        # ...=&reg_id=... into ...=®_id=A
        # That should be fixed, but in the mean time we shouldn't crash
        request = RequestFactory().get("/", {"i": "u\xae_id=A"})
        SessionMiddleware().process_request(request)
        AuthenticationMiddleware().process_request(request)
        UserServiceMiddleware().process_request(request)

        request.user = User.objects.create_user(username='tbu_user',
                                                email='fake@fake',
                                                password='top_secret')

        backend = "authz_group.authz_implementation.all_ok.AllOK"
        with self.settings(RESTCLIENTS_ADMIN_GROUP="ok",
                           AUTHZ_GROUP_BACKEND=backend):

            # Add the testing DAO service
            SERVICES["test"] = "rc_django.tests.test_views.TEST_DAO"
            res = proxy(request, "test", "/fake/")
            self.assertEquals(
                res.content, "Bad URL param given to the restclients browser")
            self.assertEquals(res.status_code, 200)
            del SERVICES["test"]

    @skipIf(missing_url("restclients_proxy", args=["test", "/ok"]),
            "restclients urls not configured")
    def test_support_links(self):
        SERVICES["test"] = "rc_django.tests.test_views.TEST_DAO"
        get_user('test_view')
        self.client.login(username='test_view',
                          password=get_user_pass('test_view'))

        response = self.client.get("/view/test/test/v1")
        self.assertEquals(response.status_code, 200)
        del SERVICES["test"]

    def test_service_errors(self):
        get_user('test_view')
        self.client.login(
            username='test_view', password=get_user_pass('test_view'))

        # Unknown service
        response = self.client.get("/view/999/test/v1")
        self.assertEquals(response.status_code, 404)
        self.assertEquals(response.content, "Unknown service: 999")

        # Missing service
        response = self.client.get("/view/pws/test/v1")
        self.assertEquals(response.status_code, 404)
        self.assertEquals(response.content, "Missing service: pws")

    def test_get_class(self):
        self.assertEquals(
            get_class("rc_django.tests.test_views.TEST_DAO"), TEST_DAO)
        self.assertRaises(
            ImportError, get_class, "uw_pws.dao.PWS_DAO")
        self.assertRaises(
            AttributeError, get_class, "rc_django.tests.test_views.fake")
        self.assertRaises(ValueError, get_class, "Fake")
