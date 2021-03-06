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

"""Look up a URL shortener by name."""


__all__ = [
    'Short',
    ]


import re

from urllib.parse import quote

from friends.utils.base import LINKIFY_REGEX as replace_urls
from friends.utils.http import Downloader


# These strings define the shortening services. If you want to add a
# new shortener to this list, the shortening service must take the URL
# as a parameter, and return the plaintext URL as the result. No JSON
# or XML parsing is supported. The strings below must contain exactly
# one instance of '{}' to represent where the long URL goes in the
# service. This is typically at the very end, but doesn't have to be.
URLS = {
    'is.gd':       'http://is.gd/api.php?longurl={}',
    'linkee.com':  'http://api.linkee.com/1.0/shorten?format=text&input={}',
    'ou.gd':       'http://ou.gd/api.php?format=simple&action=shorturl&url={}',
    'tinyurl.com': 'http://tinyurl.com/api-create.php?url={}',
    'durl.me':     'http://durl.me/api/Create.do?type=json&longurl={}',
    }


class Short:
    """Each instance of this class represents a unique shortening service."""

    def __init__(self, domain=None):
        """Determine which shortening service this instance will use."""
        self.template = URLS.get(domain)
        self.domain = domain

        # Disable shortening if no shortener found.
        if None in (domain, self.template):
            self.make = lambda url: url
            return

        if "json" in self.template:
            self.make = self.json

    def make(self, url):
        """Shorten the URL by querying the shortening service."""
        if Short.already(url):
            # Don't re-shorten an already-short URL.
            return url
        return Downloader(
            self.template.format(quote(url, safe=''))).get_string().strip()

    def sub(self, message):
        """Find *all* of the URLs in a string and shorten all of them."""
        return replace_urls(lambda match: self.make(match.group(0)), message)

    def json(self, url):
        """Grab URLs swiftly with regex."""
        # Avoids writing JSON code that is service-specific.
        find = re.compile('https?://{}[^\"]+'.format(self.domain)).findall
        for short in find(Short.make(self, url)):
            return short
        return url

    # Used for checking if URLs have already been shortened.
    already = re.compile(r'https?://({})/'.format('|'.join(URLS))).match
