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

"""Main friends-service module.

This gets turned into a script by `python3 setup.py install`.
"""


__all__ = [
    'main',
    ]


import sys
import logging

from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import Gio, GLib, GObject

GObject.threads_init(None)

from friends.service.connection import ConnectionMonitor
from friends.service.dispatcher import Dispatcher
from friends.service.shortener import URLShorten
from friends.utils.avatar import Avatar
from friends.utils.base import initialize_caches
from friends.utils.logging import initialize
from friends.utils.menus import MenuManager
from friends.utils.model import prune_model
from friends.utils.options import Options


# Optional performance profiling module.
yappi = None


# Logger must be initialized before it can be used.
log = None


def main():
    global log
    # Initialize command line options.
    args = Options().parser.parse_args()

    if args.list_protocols:
        from friends.utils.manager import protocol_manager
        for name in sorted(protocol_manager.protocols):
            cls = protocol_manager.protocols[name]
            package, dot, class_name = cls.__name__.rpartition('.')
            print(class_name)
        return

    if args.performance:
        try:
            import yappi
        except ImportError:
            pass
        else:
            yappi.start()

    # Initialize the logging subsystem.
    gsettings = Gio.Settings.new('com.canonical.friends')
    initialize(console=args.console,
               debug=args.debug or gsettings.get_boolean('debug'))
    log = logging.getLogger(__name__)
    log.info('Friends backend service starting')

    # Expire old Avatars. Without this we would never notice when
    # somebody changes their avatar, we would just keep the stale old
    # one forever.
    Avatar.expire_old_avatars()

    # mhr3 says that we should not let a Dee.SharedModel exceed 8mb in
    # size, because anything larger will have problems being transmitted
    # over DBus. I have conservatively calculated our average row length
    # to be 500 bytes, which means that we shouldn't let our model exceed
    # approximately 16,000 rows. However, that seems like a lot to me, so
    # I'm going to set it to 8,000 for now and we can tweak this later if
    # necessary. Do you really need more than 8,000 tweets in memory at
    # once? What are you doing with all these tweets?
    prune_model(8000)

    # This builds two different indexes of our persisted Dee.Model
    # data for the purposes of faster duplicate checks.
    initialize_caches()

    # Set up the DBus main loop.
    DBusGMainLoop(set_as_default=True)
    loop = GLib.MainLoop()

    refresh_interval = max(gsettings.get_int('interval'), 5) * 60

    # Load up the various services.  We do it this way so that we retain
    # references to the service endpoints without pyflakes screaming at us
    # about unused local variables.
    class services:
        connection = ConnectionMonitor()
        dispatcher = Dispatcher(loop, refresh_interval)
        menus = MenuManager(dispatcher.Refresh, loop.quit)
        shorten = URLShorten(gsettings)

    if args.test:
        # This module is only necessary if we're running the unit tests.
        from friends.testing.service import TestService
        services.test = TestService(services.connection)
    try:
        log.info('Starting friends-service main loop')
        loop.run()
    except KeyboardInterrupt:
        log.info('Stopped friends-service main loop')

    if args.performance and yappi is not None:
        yappi.print_stats(sys.stdout, yappi.SORTTYPE_TTOT)


if __name__ == '__main__':
    # Use this with `python3 -m friends.main`
    main()
