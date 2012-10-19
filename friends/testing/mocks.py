# friends-service -- send & receive messages from any social network
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

"""Mocks, doubles, and fakes for testing."""

__all__ = [
    'FakeOpen',
    'FakeSoupMessage',
    'LogMock',
    'SettingsIterMock',
    ]


import os
import hashlib
import logging

from io import StringIO
from logging.handlers import QueueHandler
from pkg_resources import resource_listdir, resource_string
from queue import Empty, Queue
from urllib.parse import urlsplit

from friends.utils.logging import LOG_FORMAT

try:
    # Python 3.3
    from unittest import mock
except ImportError:
    import mock


NEWLINE = '\n'


class FakeSoupMessage:
    """Mimic a Soup.Message that returns canned data."""

    def __init__(self, path, resource, charset='utf-8', headers=None,
                 response_code=200):
        # resource_string() always returns bytes.
        self._data = resource_string(path, resource)
        self.call_count = 0
        self._charset = charset
        self._headers = {} if headers is None else headers
        self.status_code = response_code

    @property
    def response_body(self):
        return self

    @property
    def response_headers(self):
        return self

    @property
    def request_headers(self):
        return self

    def flatten(self):
        return self

    def get_data(self):
        return self._data

    def get_as_bytes(self):
        return self._data

    def get_content_type(self):
        return 'application/x-mock-data', dict(charset=self._charset)

    def get_uri(self):
        pieces = urlsplit(self.url)
        class FakeUri:
            host = pieces.netloc
            path = pieces.path
        return FakeUri()

    def get(self, header, default=None):
        return self._headers.get(header, default)

    def append(self, header, value):
        self._headers[header] = value

    def set_request(self, *args):
        pass

    def new(self, method, url):
        self.call_count += 1
        self.method = method
        self.url = url
        return self


# A test double which shortens the given URL by returning the hex hash of the
# source URL.
class FakeOpen:
    """Mimic the object returned from urlopen()."""

    def __init__(self, url):
        # hashlib requires the input to be bytes.
        if isinstance(url, str):
            self.url = url.encode('utf-8')
        else:
            assert isinstance(url, bytes)
            self.url = url

    def read(self):
        return hashlib.md5(self.url).hexdigest()

    def __enter__(self):
        return self

    def __exit__(self, *args, **kws):
        # This must pretend to be a context manager, but there's no resource
        # that needs closing.
        pass


class SettingsIterMock:
    """Mimic the weird libaccounts AgAccountSettingIter semantics.

    The default Python mapping of this object does not follow standard Python
    iterator semantics.
    """

    def __init__(self):
        self.items = [(True, 'send_enabled', True)]

    def next(self):
        if self.items:
            return self.items.pop()
        else:
            return (False, None, None)


class LogMock:
    """A mocker for capturing logging output in protocol classes.

    This ensures that the standard friends.service log file isn't polluted by
    the tests, and that the logging output in a sub-thread can be tested in
    the main thread.

    This class can be used either in a TestCase's setUp() and tearDown()
    methods, or as a context manager (i.e. in a `with` statement).  When used
    as the latter, be sure to capture the contents of the log inside the
    with-clause since exiting the context manager will consume all left over
    log contents.

    Pass in the list of modules to mock, and it will mock all the 'log'
    attributes on those modules.  The last component can be a '*' wildcard in
    which case it will mock all the modules found in that package.
    Instantiating this class automatically starts the mocking; call the
    .empty() method to gather the accumulated log messages, even from a
    sub-thread.  In the .tearDown(), call .stop() to stop mocking.
    """
    def __init__(self, *modules):
        self._queue = Queue()
        self._log = logging.getLogger(__name__)
        handler = QueueHandler(self._queue)
        formatter = logging.Formatter(LOG_FORMAT, style='{')
        handler.setFormatter(formatter)
        self._log.addHandler(handler)
        # Capture effectively everything.  This can't be NOTSET because by
        # definition, that propagates log messages to the root logger.
        self._log.setLevel(1)
        self._log.propagate = False
        # Create the mock, and then go through all the named modules, mocking
        # their 'log' attribute.
        self._patchers = []
        for path in modules:
            prefix, dot, module = path.rpartition('.')
            if module == '*':
                # Partition again to get the parent package.
                subprefix, dot, parent = prefix.rpartition('.')
                for filename in resource_listdir(subprefix, parent):
                    basename, extension = os.path.splitext(filename)
                    if extension != '.py':
                        continue
                    patch_path = '{}.{}.__dict__'.format(prefix, basename)
                    patcher = mock.patch.dict(patch_path, {'log': self._log})
                    self._patchers.append(patcher)
            else:
                patch_path = '{}.__dict__'.format(path)
                patcher = mock.patch.dict(patch_path, {'log': self._log})
                self._patchers.append(patcher)
        # Start all the patchers.
        for patcher in self._patchers:
            patcher.start()

    def stop(self):
        # Empty the queue for test isolation.
        self.empty()
        for patcher in self._patchers:
            patcher.stop()
        # Get rid of the friends.test logger.
        del logging.Logger.manager.loggerDict['friends.test']

    def empty(self, trim=True):
        """Return all the log messages written to this log.

        :param trim: Trim exception text to just the first and last line, with
            ellipses in between.  You will usually want to do this since the
            exception details will contain file tracebacks with paths specific
            to your testing environment.
        :type trim: bool
        """
        output = StringIO()
        while True:
            try:
                record = self._queue.get_nowait()
            except Empty:
                # The queue is exhausted.
                break
            # We have to print both the message, and explicitly the exc_text,
            # otherwise we won't see the exception traceback in the output.
            args = [record.getMessage()]
            if record.exc_text is None:
                # Nothing to include.
                pass
            elif trim:
                exc_lines = record.exc_text.splitlines()
                # Leave just the first and last lines, but put ellipses in
                # between.
                exc_lines[1:-1] = [' ...']
                args.append(NEWLINE.join(exc_lines))
            else:
                args.append(record.exc_text)
            print(*args, file=output)
        return output.getvalue()

    def __enter__(self):
        return self

    def __exit__(self, *exception_info):
        self.stop()
        return False
