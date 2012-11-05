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

"""Convenient uploading."""

__all__ = [
    'Uploader',
    ]

import logging

from base64 import encodebytes
from gi.repository import Soup, GdkPixbuf
from urllib.parse import urlencode

from friends.utils.download import _soup


log = logging.getLogger(__name__)


class Uploader:
    """Convenient uploading wrapper."""

    def __init__(self, url, filename, description=''):
        self.url = url
        self.filename = filename
        self.description = description

    def send(self):
        data = GdkPixbuf.Pixbuf.new_from_file(self.filename)
        jpeg = data.save_to_bufferv('jpeg', [], [])[1]
        body = Soup.Buffer.new([byte for byte in jpeg])

        multipart = Soup.Multipart.new('multipart/form-data')
        multipart.append_form_string('message', self.description)
        multipart.append_form_file(
            'source', self.filename, 'image/jpeg', body)
        message = Soup.form_request_new_from_multipart(self.url, multipart)
        _soup.send_message(message)
        log.debug('{}: {}'.format(message.status_code, message.reason_phrase))
        return message
