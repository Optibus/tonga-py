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
        m.get('{}/flag_value/flag_name'.format(server_url), json=dict(value=True))
        client = TongaClient(server_url)
        flag_value = client.get("flag_name")
        # assertTrue return true if bool(flag_value) is True, hence we use equals to check if the value is actually True
        self.assertEqual(True, flag_value)

    @requests_mock.Mocker()
    def test_on_demand_fetch_single_boolean_flag_with_context_attributes(self, m):
        server_url = "http://server_url"
        m.get('{}/flag_value/flag_name?user=some+user1&some_attribute=2'.format(server_url), json=dict(value=True))
        m.get('{}/flag_value/flag_name?user=some+user2&some_attribute=2'.format(server_url), json=dict(value=False))
        m.get('{}/flag_value/flag_name?user=some+user2&some_attribute=3'.format(server_url), status_code=404)
        client = TongaClient(server_url, context_attributes=dict(user='some user1', some_attribute=2))
        flag_value = client.get("flag_name")
        self.assertEqual(True, flag_value)

        client = TongaClient(server_url, context_attributes=dict(user='some user2', some_attribute=2))
        flag_value = client.get("flag_name")
        self.assertEqual(False, flag_value)

        client = TongaClient(server_url, context_attributes=dict(user='some user2', some_attribute=3))
        flag_value = client.get("flag_name")
        self.assertIsNone(flag_value)

    @requests_mock.Mocker()
    def test_on_demand_fetch_single_boolean_flag_cached_result(self, m):
        server_url = "http://server_url"
        m.get('{}/flag_value/flag_name'.format(server_url), json=dict(value=True))
        client = TongaClient(server_url)
        flag_value = client.get("flag_name")
        self.assertEqual(True, flag_value)
        flag_value = client.get("flag_name")
        self.assertEqual(True, flag_value)
        self.assertEqual(1, m.call_count)

    @requests_mock.Mocker()
    def test_offline_mode_fetch(self, m):
        server_url = "http://server_url"
        m.get('{}/flag_value/flag_name'.format(server_url), text="true")
        client = TongaClient(server_url, options=TongaClientOptions(offline_mode=True))
        flag_value = client.get("flag_name", offline_value=False)
        self.assertEqual(False, flag_value)
        self.assertFalse(m.called)

    @requests_mock.Mocker()
    def test_on_demand_fetch_single_boolean_flag_with_context_and_request_attributes(self, m):
        server_url = "http://server_url"
        m.get('{}/flag_value/flag_name?user=some+user1&some_attribute=2'.format(server_url), json=dict(value=True))
        client = TongaClient(server_url, context_attributes=dict(user='some user1', some_attribute=2),
                             request_attributes=dict(attr1='val1', attr2='val2'))
        flag_value = client.get("flag_name")
        self.assertEqual(True, flag_value)
        self.assertEqual('val1', m.last_request.headers['X-Tonga-attr1'])
        self.assertEqual('val2', m.last_request.headers['X-Tonga-attr2'])


if __name__ == '__main__':
    unittest.main()
