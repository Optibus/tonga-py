from time import sleep

import json

import unittest

import requests_mock

from tonga import TongaClient, TongaClientOptions


class TestClient(unittest.TestCase):
    def test_basic_init(self):
        server_url = "http://server_url"
        TongaClient(server_url)

    @requests_mock.Mocker()
    def test_on_demand_fetch_single_non_existing_flag(self, m):
        server_url = "http://server_url"
        m.get('{}/flag_value/flag_name'.format(server_url), status_code=404)
        client = TongaClient(server_url)
        flag_value = client.get("flag_name")
        self.assertIsNone(flag_value)

    @requests_mock.Mocker()
    def test_on_demand_fetch_single_boolean_flag(self, m):
        server_url = "http://server_url"
        m.get('{}/flag_value/flag_name'.format(server_url), text="true")
        client = TongaClient(server_url)
        flag_value = client.get("flag_name")
        self.assertTrue(flag_value)

    @requests_mock.Mocker()
    def test_on_demand_fetch_single_boolean_flag_with_context_attributes(self, m):
        server_url = "http://server_url"
        m.get('{}/flag_value/flag_name?user=some+user1&some_attribute=2'.format(server_url), text="true")
        m.get('{}/flag_value/flag_name?user=some+user2&some_attribute=2'.format(server_url), text="false")
        m.get('{}/flag_value/flag_name?user=some+user2&some_attribute=3'.format(server_url), status_code=404)
        client = TongaClient(server_url, context_attributes=dict(user='some user1', some_attribute=2))
        flag_value = client.get("flag_name")
        self.assertTrue(flag_value)

        client = TongaClient(server_url, context_attributes=dict(user='some user2', some_attribute=2))
        flag_value = client.get("flag_name")
        self.assertFalse(flag_value)

        client = TongaClient(server_url, context_attributes=dict(user='some user2', some_attribute=3))
        flag_value = client.get("flag_name")
        self.assertIsNone(flag_value)

    @requests_mock.Mocker()
    def test_on_demand_fetch_single_boolean_flag_cached_result(self, m):
        server_url = "http://server_url"
        m.get('{}/flag_value/flag_name'.format(server_url), text="true")
        client = TongaClient(server_url)
        flag_value = client.get("flag_name")
        self.assertTrue(flag_value)
        flag_value = client.get("flag_name")
        self.assertTrue(flag_value)
        self.assertEqual(1, m.call_count)

    @requests_mock.Mocker()
    def test_send_analytics_on_close(self, m):
        server_url = "http://server_url"
        m.get('{}/flag_value/flag_name1?user=some+user1&some_attribute=2'.format(server_url), text="true")
        m.get('{}/flag_value/flag_name2?user=some+user1&some_attribute=2'.format(server_url), text="false")
        m.get('{}/flag_value/flag_name3?user=some+user1&some_attribute=2'.format(server_url), status_code=404)
        post = m.post('{}/update_analytics?user=some+user1&some_attribute=2'.format(server_url), status_code=200)
        client = TongaClient(server_url, context_attributes=dict(user='some user1', some_attribute=2))
        client.get("flag_name1")
        client.get("flag_name1")
        client.get("flag_name2")
        client.get("flag_name3")

        client.close()
        self.assertTrue(post.called)
        self.assertDictEqual({'flag_name1': {"true": 2}, "flag_name2": {"false": 1}, "flag_name3": {"null": 1}},
                             json.loads(post.last_request.json()))

    @requests_mock.Mocker()
    def test_send_analytics_periodically_and_not_duplicated(self, m):
        server_url = "http://server_url"
        m.get('{}/flag_value/flag_name1?user=some+user1&some_attribute=2'.format(server_url), text="true")
        post = m.post('{}/update_analytics?user=some+user1&some_attribute=2'.format(server_url), status_code=200)
        client = TongaClient(server_url, context_attributes=dict(user='some user1', some_attribute=2),
                             options=TongaClientOptions(analytics_report_interval=0.01))
        client.get("flag_name1")
        sleep(0.1)
        self.assertEqual(1, post.call_count)
        self.assertDictEqual({'flag_name1': {"true": 1}}, json.loads(post.last_request.json()))
        client.get("flag_name1")
        sleep(0.1)
        self.assertEqual(2, post.call_count)
        self.assertDictEqual({'flag_name1': {"true": 1}}, json.loads(post.last_request.json()))
        client.close()
        # We dont expect more calls as no new calls were made since last report
        self.assertEqual(2, post.call_count)


if __name__ == '__main__':
    unittest.main()
