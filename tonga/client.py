from threading import Lock, Thread, Event
from collections import defaultdict, Counter
import json
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
        :param options: Optional parameters defining the behavior of the client
        :type options: TongaClientOptions
        """
        self.server_url = server_url
        self.context_attributes = context_attributes or {}
        self.options = options or TongaClientOptions()
        self._flag_cache = {}
        self._analytics_counter = defaultdict(Counter)
        self._analytics_lock = Lock()
        self._stop_event = Event()
        self._started = False

    def get(self, flag):
        """
        Gets the value associated to the specified flag
        at the server
        :param flag: Flag name
        :type flag: str
        :return: Flag value if defined, otherwise None
        :rtype: Any
        """
        self._ensure_started()
        value = self._get_flag_value_through_cache(flag)
        with self._analytics_lock:
            self._analytics_counter[flag][json.dumps(value)] += 1
        return value

    def close(self):
        """
        Closes the client and underlying resources and flush any missing pending analytics report
        """
        self._stop_event.set()

        if not self._started:
            return

        try:
            self._update_analytics_thread.join(self.options.timeout_on_close)
        except RuntimeError:
            # If thread was not started
            pass

    def _ensure_started(self):
        """
        We want to start underlying resources in lazy manner only if the client is actually being used, this method
        will start the client if needed and if its already started it will do nothing
        """
        if self._started:
            return

        self._update_analytics_thread = Thread(target=self._update_analytics_loop, name="Tonga Analytics Thread")
        self._update_analytics_thread.setDaemon(True)
        self._update_analytics_thread.start()
        self._started = True

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

    def _update_server_analytics(self):
        """
        Sends an update of accumulated analytics to the server, if none is accumulated since last invocation
        this method does nothing
        """
        update = False
        with self._analytics_lock:
            if self._analytics_counter:
                update = True
                request_string = u'{server_url}/update_analytics'.format(server_url=self.server_url)
                request_string += self._build_query_string()
                analytics_body = json.dumps(self._analytics_counter)
                self._analytics_counter.clear()
        # Update out side of lock not to block threads waiting of network request
        if update:
            requests.post(request_string, json=analytics_body)

    def _update_analytics_loop(self):
        """
        Runs the analytics update loop in a dedicated thread
        """
        while not self._stop_event.is_set():
            self._update_server_analytics()
            self._stop_event.wait(self.options.analytics_report_interval)

        # Flush any pending analytics
        self._update_server_analytics()


class TongaClientOptions(object):
    """
    Configuration class for different options of the Tonga Client behavior
    """
    def __init__(self, analytics_report_interval=5, timeout_on_close=5):
        """
        :param timeout_on_close: How much to wait for underlying resources to gracefully close (seconds)
        :type timeout_on_close: float
        :param analytics_report_interval: Analytics thread interval between each report to the server (seconds)
        :type analytics_report_interval: float
        """
        self.analytics_report_interval = analytics_report_interval
        self.timeout_on_close = timeout_on_close
