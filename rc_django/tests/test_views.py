# Copyright 2021 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

# -*- coding: utf-8 -*-
from django.test import TestCase
from django.conf import settings
from django.test.utils import override_settings
from django.contrib.auth.models import User
from django.urls import reverse
from restclients_core.dao import DAO, MockDAO
from restclients_core.models import MockHTTP
from rc_django.views.rest_proxy import RestSearchView, RestProxyView


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
        url = reverse("restclients_proxy", args=["test", "test/v1"])
        response = self.client.get(url)
        self.assertEquals(response.status_code, 401)

        url = reverse("restclients_customform", args=["test", "index.html"])
        response = self.client.get(url)
        self.assertEquals(response.status_code, 401)


@override_settings(
    RESTCLIENTS_ADMIN_AUTH_MODULE='rc_django.tests.can_proxy_restclient')
class RestProxyViewTest(TestCase):
    def test_bad_url(self):
        # Something was sending urls that should have been
        # ...=&reg_id=... into ...=®_id=A
        # That should be fixed, but in the mean time we shouldn't crash
        url = reverse("restclients_proxy", args=[
            "test", "test/v2?i=u\xae_id=A"])
        get_user('test_view')
        self.client.login(username='test_view',
                          password=get_user_pass('test_view'))

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_format_search_params(self):
        url = 'https://test.edu/api/test?a=one&b=two&c=one%20two'
        self.assertEqual(RestProxyView.format_search_params(url), {
            'a': 'one', 'b': 'two', 'c': 'one two'})

    def test_support_links(self):
        url = reverse("restclients_proxy", args=["test", "test/v1"])
        get_user('test_view')
        self.client.login(username='test_view',
                          password=get_user_pass('test_view'))

        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)

        url = reverse("restclients_proxy", args=[
            "test", "test/v1?a=one&b=two&c=one%20two"])
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)

    def test_service_errors(self):
        get_user('test_view')
        self.client.login(
            username='test_view', password=get_user_pass('test_view'))

        # Unauthorized service
        url = reverse("restclients_proxy", args=["secret", "test/v1"])
        response = self.client.get(url)
        self.assertEquals(response.status_code, 401)

        # Missing service
        url = reverse("restclients_proxy", args=["fake", "test/v1"])
        response = self.client.get(url)
        self.assertEquals(response.status_code, 404)
        self.assertIn(b"Missing service: fake", response.content)


@override_settings(
    RESTCLIENTS_ADMIN_AUTH_MODULE='rc_django.tests.can_proxy_restclient')
class RestSearchViewTest(TestCase):
    def test_get_context_data(self):
        context = RestSearchView().get_context_data(**{})
        self.assertEqual(context["wrapper_template"], "proxy_wrapper.html")

    def test_search_post(self):
        get_user('test_view')
        self.client.login(username='test_view',
                          password=get_user_pass('test_view'))

        # hfs, missing form values
        url = reverse("restclients_customform", args=["hfs", "accounts"])
        response = self.client.post(url)
        self.assertEquals(response.status_code, 400)
        self.assertIn(b"Missing reqired form value: 'uwnetid'",
                      response.content)

        # hfs
        url = reverse("restclients_customform", args=["hfs", "accounts"])
        response = self.client.post(url, {"uwnetid": "\xae"})
        self.assertEquals(response.status_code, 302)
        self.assertEqual(response.url, "/view/hfs/myuw/v1/%C2%AE")

        url = reverse("restclients_customform", args=["hfs", "accounts"])
        response = self.client.post(url, {"uwnetid": "javerage"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/view/hfs/myuw/v1/javerage")

        # bookstore
        url = reverse("restclients_customform", args=["book", "store"])
        response = self.client.post(url, {
            "sln1": "123", "quarter": "spring", "returnlink": "t"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, (
            "/view/book/uw/json_utf8_202007.ubs?"
            "sln1=123&quarter=spring&returnlink=t"))

        # myplan
        url = reverse("restclients_customform", args=["myplan", "plan"])
        response = self.client.post(url, {
            "uwregid": "ABC", "year": "2013", "quarter": "spring"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url,
                         "/view/myplan/student/api/plan/v1/2013,spring,1,ABC")

        # libraries
        url = reverse("restclients_customform", args=["libraries", "accounts"])
        response = self.client.post(url, {"id": "javerage"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url,
                         "/view/libraries/mylibinfo/v1/?id=javerage")

        # iasystem
        url = reverse("restclients_customform", args=[
            "iasystem_uw", "uw/api/v1/evaluation"])
        response = self.client.post(url, {"student_id": "123456"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, (
            "/view/iasystem_uw/api/v1/evaluation?student_id=123456"))

        # uwnetid
        url = reverse("restclients_customform", args=["uwnetid", "password"])
        response = self.client.post(url, {"uwnetid": "javerage"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url,
                         "/view/uwnetid/nws/v1/uwnetid/javerage/password")

        # grad
        url = reverse("restclients_customform", args=[
            "grad", "services/students/v1/api/committee"])
        response = self.client.post(url, {
            "id": "12345", "csrfmiddlewaretoken": "0000000"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, (
            "/view/grad/services/students/v1/api/committee?id=12345"))

    def test_customform(self):
        url = reverse("restclients_customform", args=["hfs", "index.html"])

        get_user('test_view')
        self.client.login(username='no_auth',
                          password=get_user_pass('test_view'))

        # hfs, no auth
        response = self.client.get(url)
        self.assertEquals(response.status_code, 302)
        self.assertTrue("next=/search/hfs/index.html" in response.url)

        # hfs, auth
        get_user('test_view')
        self.client.login(username='test_view',
                          password=get_user_pass('test_view'))
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertIn(b'<form method="post" action="/search/hfs/index">',
                      response.content)

        # iasystem
        url = reverse("restclients_customform", args=[
            "iasystem", "uw/api/v1/evaluation.html"])
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertIn(b'action="/search/iasystem/uw/api/v1/evaluation">',
                      response.content)
