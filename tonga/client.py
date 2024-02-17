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
        self._pre_fetched = False

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
        if self.options.pre_fetch:
            return self._pre_fetch_if_needed_and_get_flag(flag)

        value = self._get_flag_value_from_server(flag)
        self._flag_cache[flag] = value
        return value

    def _pre_fetch_if_needed_and_get_flag(self, flag):
        """
        Pre-fetches all flags and then gets the flag value from the cache
        :param flag: Flag name
        :type flag: str
        :return: Flag value if defined, otherwise None
        :rtype: Any
        """
        # If we are here, it means that the flag is not in the cache, but we are in pre-fetch mode, so we can safely
        # assume that the flag is not in the cache because it was not available while pre-fetching, so we can return
        # None without making a request to the server
        if self._pre_fetched:
            return None

        request_string = u"{server_url}/all_flags_values".format(server_url=self.server_url)
        request_string += self._build_query_string()
        headers = self._build_headers()
        response_json = self._get_from_server_with_retries(request_string, headers)
        pre_fetched = response_json if response_json else {}
        self._populate_cache_from_pre_fetched(pre_fetched)
        self._pre_fetched = True
        return self._flag_cache.get(flag)

    def _populate_cache_from_pre_fetched(self, pre_fetched, prefix=""):
        """
        Populates the cache with the pre-fetched flags
        :param pre_fetched: Pre-fetched flags
        :type pre_fetched: dict[str, Any]
        :param prefix: Prefix to add to the flag names
        :type prefix: str
        """
        # The pre-fetched is a dictionary with any depth, so we need to recursively populate the cache and add the
        # prefix to the keys in order to flatten the structure into a single level dictionary with the full flag names
        for key, value in pre_fetched.items():
            if not isinstance(value, dict):
                self._flag_cache[prefix + key] = value
            else:
                # Recursively populate the cache
                self._populate_cache_from_pre_fetched(value, prefix + key + ".")

    def _get_flag_value_from_server(self, flag):
        """
        Fetch the flag value from the server
        :param flag: Flag name
        :type flag: str
        :return: Flag value if defined, otherwise None
        :rtype: Any
        """
        request_string = u"{server_url}/flag_value/{flag}".format(server_url=self.server_url, flag=flag)
        request_string += self._build_query_string()
        headers = self._build_headers()
        response_json = self._get_from_server_with_retries(request_string, headers)
        return response_json.get("value") if response_json else None

    def _get_from_server_with_retries(self, request_string, headers):
        """
        Fetch request data from the server with retries
        :param request_string: Request string
        :type request_string: str
        :param headers: Request headers
        :type headers: dict[str, str]
        :return: Flag value if defined, otherwise None
        :rtype: dict or None
        """
        for attempt in range(self.options.retries + 1):
            try:
                response = requests.get(request_string, headers=headers)
                if response.status_code == 404:
                    return None
                # Check for error code
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException:
                # Upon last retry, raise original error
                if attempt == self.options.retries:
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
        return {
            u"X-Tonga-{key}".format(key=key): six.ensure_str(six.text_type(value))
            for key, value in self.request_attributes.items()
            if value is not None
        }

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
    def __init__(self, offline_mode=False, retries=10, retry_delay=1, pre_fetch=False):
        """
        :param offline_mode: Whether to operate in offline mode, not interacting with the server for fetching values.
        This is useful for when running tests and there is no backend available or it should not be used
        :type offline_mode: bool
        :param retries: Number of retries when failing to get a flag
        :type retries: int
        :param retry_delay: Delay between each retry attempt in seconds
        :type retry_delay: float
        :param pre_fetch: Whether to pre-fetch all flags when a flag is requested, this is useful when you want to
        avoid multiple requests to the server when you know you will need multiple flags
        :type pre_fetch: bool
        """
        self.offline_mode = offline_mode
        self.retries = retries
        self.retry_delay = retry_delay
        self.pre_fetch = pre_fetch
