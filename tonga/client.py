import urllib
import requests
import six


class TongaClient(object):
    def __init__(self, server_url, context_attributes=None, options=None):
        """
        :param server_url: Server connection string
        :type server_url: str
        :param context_attributes: Optional context attributes to be passed on each query
        :type context_attributes: dict[str, object]
        :param options: Client optional configuration
        :type options: TongaClientOptions
        """
        self.server_url = server_url
        self.context_attributes = context_attributes or {}
        self.options = options or TongaClientOptions()
        self._flag_cache = {}

    def get(self, flag, offline_value=None):
        """
        Gets the value associated to the specified flag
        at the server
        :param flag: Flag name
        :type flag: str
        :param offline_value: Which value to return if client is in offline mode
        :type offline_value: Any
        :return: Flag value if defined, otherwise None
        :rtype: Any
        """
        if self.options.offline_mode:
            return offline_value
        return self._get_flag_value_through_cache(flag)

    def _get_flag_value_through_cache(self, flag):
        """
        Gets the value associated to the specified flag going through the cached values first, and if not found checking
        at the server
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
        request_string = u'{server_url}/flag_value/{flag}'.format(server_url=self.server_url, flag=flag)
        request_string += self._build_query_string()
        response = requests.get(request_string)
        if response.status_code == 404:
            return None
        # Check for error code
        response.raise_for_status()
        return response.json()

    def _build_query_string(self):
        """
        Creates a query string from the context attributes
        :return: Query string to attach to the request url
        :rtype: str
        """
        if six.PY2:
            query_string = urllib.urlencode(self.context_attributes)  # pylint: disable=maybe-no-member
        else:
            query_string = urllib.parse.urlencode(self.context_attributes)
        if query_string:
            return u"?" + query_string
        return ""


class TongaClientOptions(object):
    def __init__(self, offline_mode=False):
        self.offline_mode = offline_mode
