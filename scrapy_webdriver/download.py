import logging
from scrapy import version_info
from scrapy.utils.decorators import inthread
from scrapy.utils.misc import load_object
from selenium.webdriver.support.wait import WebDriverWait

from .http import WebdriverActionRequest, WebdriverRequest, WebdriverResponse

if list(map(int, version_info)) < [0, 18]:
    FALLBACK_HANDLER = 'http.HttpDownloadHandler'
elif list(map(int, version_info)) >= [0, 24, 4]:
    FALLBACK_HANDLER = 'http.HTTPDownloadHandler'
else:
    FALLBACK_HANDLER = 'http10.HTTP10DownloadHandler'
FALLBACK_HANDLER = 'scrapy.core.downloader.handlers.%s' % FALLBACK_HANDLER


class WebdriverDownloadHandler(object):
    """This download handler uses webdriver, deferred in a thread.

    Falls back to the stock scrapy download handler for non-webdriver requests.

    """
    def __init__(self, settings):
        self._enabled = settings.get('WEBDRIVER_BROWSER') is not None
        self._is_ready_timeout = settings.get('WEBDRIVER_IS_READY_TIMEOUT', 60)
        self._fallback_handler = load_object(FALLBACK_HANDLER)(settings)

    def download_request(self, request, spider):
        """Return the result of the right download method for the request."""
        if self._enabled and isinstance(request, WebdriverRequest):
            if isinstance(request, WebdriverActionRequest):
                download = self._do_action_request
            else:
                download = self._download_request
        else:
            download = self._fallback_handler.download_request
        return download(request, spider)

    @inthread
    def _download_request(self, request, spider):
        """Download a request URL using webdriver."""
        logging.debug('Downloading %s with webdriver' % request.url)
        self._get_url(request)
        self._wait_until_ready(request)
        return self._build_response(request)

    @inthread
    def _do_action_request(self, request, spider):
        """Perform an action on a previously webdriver-loaded page."""
        logging.debug('Running webdriver actions %s' % request.url)
        self._perform_actions(request)
        self._wait_until_ready(request)
        return self._build_response(request)

    @staticmethod
    def _get_url(request):
        request.manager.webdriver.get(request.url)

    @staticmethod
    def _perform_actions(request):
        request.action(request.manager.webdriver)

    def _wait_until_ready(self, request):
        if hasattr(request.is_ready, '__call__'):
            if request.is_ready_timeout:
                timeout = request.is_ready_timeout
            else:
                timeout = self._is_ready_timeout
            WebDriverWait(request.manager.webdriver, timeout).until(request.is_ready)

    @staticmethod
    def _build_response(request):
        return WebdriverResponse(request.url, request.manager.webdriver)
