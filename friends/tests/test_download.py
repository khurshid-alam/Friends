# friends-dispatcher -- send & receive messages from any social network
# Copyright (C) 2012  Canonical Ltd
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Test the downloading utilities."""

__all__ = [
    'TestDownloader',
    ]


import json
import time
import datetime
import unittest
import threading

from urllib.error import URLError
from urllib.parse import parse_qs
from urllib.request import urlopen
from wsgiref.simple_server import WSGIRequestHandler, make_server
from wsgiref.util import setup_testing_defaults
from pkg_resources import resource_filename

from friends.tests.mocks import FakeSoupMessage, LogMock, mock
from friends.utils.http import Downloader, Uploader


class _SilentHandler(WSGIRequestHandler):
    def log_message(self, format, *args):
        pass


def _app(environ, start_response):
    """WSGI application for responding to test queries."""
    setup_testing_defaults(environ)
    status = '200 OK'
    results = []
    headers = [('Content-Type', 'text/plain; charset=utf-8')]
    path = environ['PATH_INFO']
    if path == '/ping':
        pass
    elif path == '/mirror':
        size = int(environ['CONTENT_LENGTH'])
        results = [environ['wsgi.input'].read(size)]
    elif path == '/json':
        results = [json.dumps(dict(answer='hello')).encode('utf-8')]
    elif path == '/post':
        # Might be a GET or POST.
        if environ['REQUEST_METHOD'] == 'POST':
            size = int(environ['CONTENT_LENGTH'])
            payload = environ['wsgi.input'].read(size)
            params = parse_qs(payload)
            # We want a mapping from strings to ints, but the POST data will
            # be utf-8 encoded byte keys and lists of length 1 with byte
            # representations of integers.  Do the conversion.
            converted = {key.decode('utf-8'): int(value[0])
                         for key, value in params.items()}
        else:
            assert environ['REQUEST_METHOD'] == 'GET'
            payload = parse_qs(environ['QUERY_STRING'])
            # We want a mapping from strings to ints, but the query string
            # will be strings and lists of length 1 with string representation
            # of integers.  Do the conversion.
            converted = {key: int(value[0])
                         for key, value in payload.items()}
        results = [json.dumps(converted).encode('utf-8')]
    elif path == '/headers':
        http_headers = {}
        for key, value in environ.items():
            if key.startswith('HTTP_X_'):
                http_headers[key[7:].lower()] = value
        results = [json.dumps(http_headers).encode('utf-8')]
    elif path == '/text':
        results = [b'hello world']
    elif path == '/bytes':
        results = [bytes.fromhex('f157f00d')]
    else:
        status = '404 Bad'
        results = [b'Missing']
    start_response(status, headers)
    return results


class TestDownloader(unittest.TestCase):
    """Test the downloading utilities."""

    def setUp(self):
        self.log_mock = LogMock('friends.utils.http')

    def tearDown(self):
        self.log_mock.stop()

    @classmethod
    def setUpClass(cls):
        cls.server = make_server('', 9180, _app, handler_class=_SilentHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever)
        cls.thread.start()
        # Wait until the server is responding.
        until = datetime.datetime.now() + datetime.timedelta(seconds=30)
        while datetime.datetime.now() < until:
            try:
                with urlopen('http://localhost:9180/ping'):
                    pass
            except URLError:
                time.sleep(0.1)
            else:
                break
        else:
            raise RuntimeError('Server thread did not start up.')

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join()

    def test_simple_json_download(self):
        # Test simple downloading of JSON data.
        self.assertEqual(Downloader('http://localhost:9180/json').get_json(),
                         dict(answer='hello'))

    @mock.patch('friends.utils.http._soup', mock.Mock())
    @mock.patch('friends.utils.http.Soup.Message',
                FakeSoupMessage('friends.tests.data',
                                'json-utf-8.dat', 'utf-8'))
    def test_json_explicit_utf_8(self):
        # RFC 4627 $3 with explicit charset=utf-8.
        self.assertEqual(Downloader('http://example.com').get_json(),
                         dict(yes='ÑØ'))

    @mock.patch('friends.utils.http._soup', mock.Mock())
    @mock.patch('friends.utils.http.Soup.Message',
                FakeSoupMessage('friends.tests.data', 'json-utf-8.dat', None))
    def test_json_implicit_utf_8(self):
        # RFC 4627 $3 with implicit charset=utf-8.
        self.assertEqual(Downloader('http://example.com').get_json(),
                         dict(yes='ÑØ'))

    @mock.patch('friends.utils.http._soup', mock.Mock())
    @mock.patch('friends.utils.http.Soup.Message',
                FakeSoupMessage('friends.tests.data',
                                'json-utf-16le.dat', None))
    def test_json_implicit_utf_16le(self):
        # RFC 4627 $3 with implicit charset=utf-16le.
        self.assertEqual(Downloader('http://example.com').get_json(),
                         dict(yes='ÑØ'))

    @mock.patch('friends.utils.http._soup', mock.Mock())
    @mock.patch('friends.utils.http.Soup.Message',
                FakeSoupMessage('friends.tests.data',
                                'json-utf-16be.dat', None))
    def test_json_implicit_utf_16be(self):
        # RFC 4627 $3 with implicit charset=utf-16be.
        self.assertEqual(Downloader('http://example.com').get_json(),
                         dict(yes='ÑØ'))

    @mock.patch('friends.utils.http._soup', mock.Mock())
    @mock.patch('friends.utils.http.Soup.Message',
                FakeSoupMessage('friends.tests.data',
                                'json-utf-32le.dat', None))
    def test_json_implicit_utf_32le(self):
        # RFC 4627 $3 with implicit charset=utf-32le.
        self.assertEqual(Downloader('http://example.com').get_json(),
                         dict(yes='ÑØ'))

    @mock.patch('friends.utils.http._soup', mock.Mock())
    @mock.patch('friends.utils.http.Soup.Message',
                FakeSoupMessage('friends.tests.data',
                                'json-utf-32be.dat', None))
    def test_json_implicit_utf_32be(self):
        # RFC 4627 $3 with implicit charset=utf-32be.
        self.assertEqual(Downloader('http://example.com').get_json(),
                         dict(yes='ÑØ'))

    def test_simple_text_download(self):
        # Test simple downloading of text data.
        self.assertEqual(Downloader('http://localhost:9180/text').get_string(),
                         'hello world')

    def test_simple_bytes_download(self):
        # Test simple downloading of bytes data.
        bytes_data = Downloader('http://localhost:9180/bytes').get_bytes()
        self.assertIsInstance(bytes_data, bytes)
        self.assertEqual(list(bytes_data), [241, 87, 240, 13])

    def test_params_post(self):
        # Test posting data.
        self.assertEqual(
            Downloader('http://localhost:9180/post',
                       params=dict(one=1, two=2, three=3),
                       method='POST').get_json(),
            dict(one=1, two=2, three=3))

    def test_params_get(self):
        # Test getting with query string URL.
        self.assertEqual(
            Downloader('http://localhost:9180/post',
                       params=dict(one=1, two=2, three=3),
                       method='GET').get_json(),
            dict(one=1, two=2, three=3))

    def test_headers(self):
        # Provide some additional headers.
        self.assertEqual(
            Downloader('http://localhost:9180/headers',
                       headers={'X-Foo': 'baz',
                                'X-Bar': 'foo'}).get_json(),
            dict(foo='baz', bar='foo'))

    def test_mirror(self):
        self.assertEqual(
            Downloader('http://localhost:9180/mirror',
                       method='POST',
                       params=dict(foo='bar')).get_string(),
            'foo=bar')

    def test_uploads(self):
        filename = resource_filename('friends.tests.data', 'ubuntu.png')
        raw_sent = Uploader(
            'http://localhost:9180/mirror',
            'file://' + filename,
            'Great logo!',
            picture_key='source',
            desc_key='message',
            foo='bar',
            ).get_bytes()
        delimiter = raw_sent[2:66]
        self.assertTrue(
            raw_sent.startswith(
                b'--' + delimiter + b'\r\nContent-Disposition: form-data; '
                b'name="foo"\r\n\r\nbar\r\n--' + delimiter +
                b'\r\nContent-Disposition: form-data; name="message"\r\n\r\n'
                b'Great logo!\r\n--' + delimiter + b'\r\nContent-Disposition: '
                b'form-data; name="source"; filename="file://' +
                filename.encode() + b'"\r\nContent-Type: '
                b'application/octet-stream\r\n\r\n\x89PNG'))
        self.assertTrue(
            raw_sent.endswith(
                b'\r\n--' + delimiter + b'--\r\n'))

    @mock.patch('friends.utils.http.Soup')
    @mock.patch('friends.utils.http._soup')
    def test_upload_happens_only_once(self, _soupmock, Soupmock):
        filename = resource_filename('friends.tests.data', 'ubuntu.png')
        Uploader(
            'http://localhost:9180/mirror',
            'file://' + filename,
            'Great logo!',
            picture_key='source',
            desc_key='message',
            foo='bar',
            ).get_bytes()
        _soupmock.send_message.assert_called_once_with(
            Soupmock.form_request_new_from_multipart())
