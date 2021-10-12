import unittest

import requests_mock

from tonga import TongaClient


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


if __name__ == '__main__':
    unittest.main()
