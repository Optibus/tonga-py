import urllib
import requests
import six


class TongaClient(object):
    def __init__(self, server_url, context_attributes=None):
        """
        :param server_url: Server connection string
        :type server_url: str
        :param context_attributes: Optional context attributes to be passed on each query
        :type context_attributes: dict[str, object]
        """
        self.server_url = server_url
        self.context_attributes = context_attributes or {}
        self._flag_cache = {}

    def get(self, flag):
        """
        Gets the value associated to the specified flag
        :param flag: Flag name
        :type flag: str
        :return: Flag value if defined, otherwise None
        :rtype: Any
        """
        if flag in self._flag_cache:
            return self._flag_cache[flag]
        value = self._get_flag_value_from_server(flag)
        self._flag_cache[flag] = value
        return value

    def _get_flag_value_from_server(self, flag):
        """
        Fetch the flag value from the server
        :param flag: Flag name
        :type flag: str
        :return: Flag value if defined, otherwise None
        :rtype: Any
        """
        if six.PY2:
            query_string = urllib.urlencode(self.context_attributes or {})
        else:
            query_string = urllib.parse.urlencode(self.context_attributes)
        request_string = u'{server_url}/flag_value/{flag}'.format(server_url=self.server_url, flag=flag)
        if query_string:
            request_string += u'?' + query_string
        response = requests.get(request_string)
        if response.status_code == 404:
            return None
        # Check for error code
        response.raise_for_status()
        return response.json()
