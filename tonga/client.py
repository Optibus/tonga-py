from time import sleep

from contextlib import contextmanager
from copy import deepcopy

import urllib
import requests
import six


class TongaClient(object):
    def __init__(self, server_url, context_attributes=None, request_attributes=None, options=None):
        """
        :param server_url: Server connection string
        :type server_url: str
        :param context_attributes: Optional context attributes to be passed on each query
        :type context_attributes: dict[str, object]
        :param request_attributes: Optional request attributes to be passed on each query, they do not affect the
        selected flag but can be used to add extra logging/monitoring information on the server side about this request
        :type request_attributes: dict[str, str]
        :param options: Client optional configuration
        :type options: TongaClientOptions
        """
        self.server_url = server_url
        self.context_attributes = context_attributes or {}
        self.request_attributes = request_attributes or {}
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
        if flag in self._flag_cache:
            return self._flag_cache[flag]

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
        headers = self._build_headers()
        for i in range(self.options.retries):
            try:
                response = requests.get(request_string, headers=headers)
                if response.status_code == 404:
                    return None
                # Check for error code
                response.raise_for_status()
                return response.json().get('value')
            except requests.exceptions.RequestException:
                # Upon last retry, raise original error
                if i == self.options.retries - 1:
                    raise
                sleep(self.options.retry_delay)

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

    def _build_headers(self):
        """
        Creates extra headers to pass as part of the request based on given request attributes
        :return: Request headers
        :rtype: dict[str, str]
        """
        return {u'X-Tonga-{key}'.format(key=key): six.ensure_str(six.text_type(value))
                for key, value in self.request_attributes.items() if value is not None}

    def dump_state(self):
        """
        Returns a dump of the current flag state of the client containing all fetched flags
        :return: Dump of fetched flag state
        :rtype: dict[str, Any]
        """
        return deepcopy(self._flag_cache)

    def set_state(self, state):
        """
        Sets the internal fetched flag state with the given state, this will override any prior fetched flags
        This is useful for testing purposes when you want to test your code under different flag states
        :param state: Flag state
        :type state: dict[str, Any]
        """
        self._flag_cache = deepcopy(state)

    def clear_state(self):
        """
        Clears current state, any following call to get will fetch the state from the backend (or offline mode)
        """
        self._flag_cache = {}

    @contextmanager
    def with_state(self, state):
        """
        Override current flag state with given state while inside the with context, once scope is exited previous state
        is restored. This is useful for tests when the client is a singleton object inside the process and each test
        should not have a side affect of changing the state for others
        :param state: Flag state
        :type state: dict[str, Any]
        """
        prev_state = self.dump_state()
        self.set_state(state)
        try:
            yield
        finally:
            self.set_state(prev_state)


class TongaClientOptions(object):
    def __init__(self, offline_mode=False, retries=10, retry_delay=1):
        """
        :param offline_mode: Whether to operate in offline mode, not interacting with the server for fetching values.
        This is useful for when running tests and there is no backend available or it should not be used
        :type offline_mode: bool
        :param retries: Number of retries when failing to get a flag
        :type retries: int
        :param retry_delay: Delay between each retry attempt in seconds
        :type retry_delay: float
        """
        self.offline_mode = offline_mode
        self.retries = retries
        self.retry_delay = retry_delay
