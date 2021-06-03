# Copyright 2021 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.test import TestCase
from rc_django.models import RestProxy
from rc_django.tests.test_views import TEST_DAO, SUB_DAO
from restclients_core.models import MockHTTP


class RestProxyTest(TestCase):
    def setUp(self):
        response = MockHTTP()
        response.status = 200
        response.data = "ok"

        self.proxy = RestProxy("pws")
        self.proxy.response = response

    def test_dao_instance(self):
        self.assertEqual(type(RestProxy("test").dao), TEST_DAO)
        self.assertEquals(type(RestProxy("test_sub").dao), SUB_DAO)

        # Missing service
        proxy = RestProxy("fake")
        self.assertRaises(ImportError, getattr, proxy, "dao")

    def test_get_mock_response(self):
        proxy = RestProxy("test_sub")
        response = proxy.get_api_response("/foo")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.data, "ok")
        self.assertTrue(isinstance(proxy.duration, float))

    def test_simple(self):
        closed = "<div/>"
        valid = "<!-- <div/> --><div></div>"

        self.assertEquals(valid, self.proxy.clean_self_closing_divs(closed))

    def test_2_simple(self):
        closed = '<div/><div id="1"/>'
        valid = ('<!-- <div/> --><div></div>'
                 '<!-- <div id="1"/> --><div id="1"></div>')

        self.assertEqual(valid, self.proxy.clean_self_closing_divs(closed))

    def test_valid_div(self):
        valid = "<div id='test_id'></div>"
        self.assertEqual(valid, self.proxy.clean_self_closing_divs(valid))

    def test_div_then_valid_self_closing(self):
        valid = "<div id='test_id'></div><br/>"
        self.assertEqual(valid, self.proxy.clean_self_closing_divs(valid))

    def test_json(self):
        content = '{"Href": "/identity/v2/entity.json"}'
        self.proxy.response.data = content
        self.assertEqual(self.proxy.json, content)

        content = '{"Decimal": 5.678}'
        self.proxy.response.data = content
        self.assertEqual(self.proxy.json, content)

    def test_format_json(self):
        json_data = '{"Href": "/identity/v2/entity.json"}'
        formatted = (u'{<br/>\n&nbsp;&nbsp;&nbsp;&nbsp;"Href":&nbsp;'
                     u'"<a href="/view/pws/identity/v2/entity.json">'
                     u'/identity/v2/entity.json</a>"<br/>\n}')
        self.proxy.response.data = json_data
        self.assertEqual(self.proxy.format_json(), formatted)

        json_data = '{"Decimal": 5.678}'
        formatted = ('{<br/>\n&nbsp;&nbsp;&nbsp;&nbsp;"Decimal":'
                     '&nbsp;5.678<br/>\n}')
        self.proxy.response.data = json_data
        self.assertEqual(self.proxy.format_json(), formatted)

        self.proxy.response.data = "<p></p>"
        self.assertRaises(ValueError, self.proxy.format_json)

    def test_format_html(self):
        output = '<a href="/view/pws/api/v1/test"></a>'

        self.proxy.response.data = '<a href="/api/v1/test"></a>'
        self.assertEqual(self.proxy.format_html(), output)

        self.proxy.response.data = '<a HREF="/api/v1/test"></a>'
        self.assertEqual(self.proxy.format_html(), output)

        # Binary string
        self.proxy.response.data = b'<a href="/api/v1/test"></a>'
        self.assertEqual(self.proxy.format_html(), output)

        # Single quotes
        self.proxy.response.data = "<a href='/api/v1/test'></a>"
        self.assertEqual(self.proxy.format_html(), output)

        # Style tags
        self.proxy.response.data = (
            '<style>h1 {color:red;}</style><a href="/api/v1/test"></a>')
        self.assertEqual(self.proxy.format_html(), output)

        self.proxy.response.data = (
            b'<STYLE>h1 {color:red;}</STYLE><a href="/api/v1/test"></a>')
        self.assertEqual(self.proxy.format_html(), output)
