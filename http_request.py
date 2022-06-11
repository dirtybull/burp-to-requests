from http.server import BaseHTTPRequestHandler
from io import BytesIO
from json import load
from urllib.parse import parse_qsl
from urllib.parse import urlparse


class HTTPRequest(BaseHTTPRequestHandler):
    def __init__(self, raw_http_request):
        self.rfile = BytesIO(raw_http_request.encode('utf-8'))
        self.raw_requestline = self.rfile.readline()
        self.error_code = self.error_message = None
        self.parse_request()
        self.parsed_url = urlparse(self.path)

        self.host = self.headers.get('Host')

        self.headers = dict(self.headers)

        # Cookies
        self.cookies = {}
        raw_cookies = self.headers.get('Cookie')
        if raw_cookies:
            for raw_cookie in raw_cookies.split(';'):
                cookie_parts = raw_cookie.split('=')
                cookie_name = cookie_parts[0].strip()
                cookie_value = ''.join(cookie_parts[1:]).strip()
                self.cookies[cookie_name] = cookie_value
            self.headers.pop('Cookie')

        # Data
        try:
            self.data = raw_http_request[raw_http_request.index(
                '\r\n\r\n')+4:].rstrip()
        except ValueError:
            self.data = None

    def send_error(self, code, message):
        self.error_code = code
        self.error_message = message
