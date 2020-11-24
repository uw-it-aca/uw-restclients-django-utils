# -*- coding: utf-8 -*-
from django.test import TestCase, RequestFactory
from django.conf import settings
from django.test.utils import override_settings
from django.contrib.auth.middleware import AuthenticationMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.models import User
from django.urls import reverse
from restclients_core.dao import DAO, MockDAO
from restclients_core.exceptions import DataFailureException
from restclients_core.models import MockHTTP
from rc_django.views import (
    proxy, clean_self_closing_divs, format_json, format_html, get_dao_instance,
    get_mock_response, format_search_params)
from userservice.user import UserServiceMiddleware
from unittest import skipIf


class TEST_DAO(DAO):
    def __init__(self):
        super(TEST_DAO, self).__init__()

    def service_name(self):
        return "test"

    def get_default_service_setting(self, key):
        if "DAO_CLASS" == key:
            return "rc_django.tests.test_views.Backend"


class SUB_DAO(TEST_DAO):
    def __init__(self):
        super(SUB_DAO, self).__init__()

    def service_name(self):
        return "test_sub"


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
        print(str(ex))
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


class ViewNoAuthTest(TestCase):
    def test_service_errors(self):
        get_user('test_view')
        self.client.login(
            username='test_view', password=get_user_pass('test_view'))

        # No auth module in settings
        url = reverse("restclients_proxy", args=["test", "/test/v1"])
        response = self.client.get(url)
        self.assertEquals(response.status_code, 401)


@override_settings(
    RESTCLIENTS_ADMIN_AUTH_MODULE='rc_django.tests.can_proxy_restclient')
class ViewTest(TestCase):
    def test_simple(self):
        self_closed = "<div/>"
        valid = "<!-- <div/> --><div></div>"

        self.assertEquals(valid, clean_self_closing_divs(self_closed))

    def test_2_simple(self):
        self_closed = '<div/><div id="1"/>'
        valid = ('<!-- <div/> --><div></div>'
                 '<!-- <div id="1"/> --><div id="1"></div>')

        self.assertEquals(valid, clean_self_closing_divs(self_closed))

    def test_valid_div(self):
        valid = "<div id='test_id'></div>"
        self.assertEquals(valid, clean_self_closing_divs(valid))

    def test_div_then_valid_self_closing(self):
        valid = "<div id='test_id'></div><br/>"
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

        # Add the testing DAO service
        response = proxy(request, "test", "/fake/")

        # Test that the bad param doesn't cause a non-200 response
        self.assertEquals(response.status_code, 200)

    def test_format_json(self):
        service = 'pws'
        json_data = '{"Href": "/identity/v2/entity.json"}'
        formatted = (u'{<br/>\n&nbsp;&nbsp;&nbsp;&nbsp;"Href":&nbsp;'
                     u'"<a href="/view/pws/identity/v2/entity.json">'
                     u'/identity/v2/entity.json</a>"<br/>\n}')
        html, raw = format_json(service, json_data)
        self.assertEquals(formatted, html)
        self.assertEquals(json_data, raw)

        json_data = '{"Decimal": 5.678}'
        formatted = ('{<br/>\n&nbsp;&nbsp;&nbsp;&nbsp;"Decimal":'
                     '&nbsp;5.678<br/>\n}')
        html, raw = format_json(service, json_data)
        self.assertEquals(formatted, html)
        self.assertEquals(json_data, raw)

        self.assertRaises(ValueError, format_json, service, '<p></p>')

    def test_format_html(self):
        service = 'pws'
        output = '<a href="/view/pws/api/v1/test"></a>'

        html = '<a href="/api/v1/test"></a>'
        self.assertEqual(format_html(service, html), output)

        html = '<a HREF="/api/v1/test"></a>'
        self.assertEqual(format_html(service, html), output)

        # Binary string
        html = b'<a href="/api/v1/test"></a>'
        self.assertEqual(format_html(service, html), output)

        # Single quotes
        html = "<a href='/api/v1/test'></a>"
        self.assertEqual(format_html(service, html), output)

        # Style tags
        html = '<style>h1 {color:red;}</style><a href="/api/v1/test"></a>'
        self.assertEqual(format_html(service, html), output)

        html = b'<STYLE>h1 {color:red;}</STYLE><a href="/api/v1/test"></a>'
        self.assertEqual(format_html(service, html), output)

    def test_format_search_params(self):
        url = 'https://test.edu/api/test?a=one&b=two&c=one%20two'
        self.assertEqual(format_search_params(url), {
            'a': 'one', 'b': 'two', 'c': 'one two'})

    @skipIf(missing_url("restclients_proxy", args=["test", "/ok"]),
            "restclients urls not configured")
    def test_support_links(self):
        url = reverse("restclients_proxy", args=["test", "/test/v1"])
        get_user('test_view')
        self.client.login(username='test_view',
                          password=get_user_pass('test_view'))

        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)

    def test_service_errors(self):
        get_user('test_view')
        self.client.login(
            username='test_view', password=get_user_pass('test_view'))

        # Unauthorized service
        url = reverse("restclients_proxy", args=["secret", "/test/v1"])
        response = self.client.get(url)
        self.assertEquals(response.status_code, 401)

        # Missing service
        url = reverse("restclients_proxy", args=["fake", "/test/v1"])
        response = self.client.get(url)
        self.assertEquals(response.status_code, 404)

    def test_get_dao_instance(self):
        self.assertEquals(type(get_dao_instance("test")), TEST_DAO)
        self.assertEquals(type(get_dao_instance('test_sub')), SUB_DAO)

        # Missing service
        self.assertRaises(ImportError, get_dao_instance, "fake")

    def test_get_mock_response(self):
        dfe = DataFailureException('/', 503, 'Service Unavailable')
        response = get_mock_response(dfe)
        self.assertIsInstance(response, MockHTTP)
        self.assertEqual(response.status, 503)
        self.assertEqual(response.data, 'Service Unavailable')
