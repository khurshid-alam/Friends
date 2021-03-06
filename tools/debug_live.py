#!/usr/bin/env python3

"""Usage: ./tools/debug_live.py PROTOCOL OPERATION [OPTIONS]

Where PROTOCOL is a protocol supported by Friends, such as 'twitter',
OPERATION is an instance method defined in that protocol's class, and OPTIONS
are whatever arguments you'd like to pass to that method (if any), such as
message id's or a status message.

Examples:

./tools/debug_live.py twitter home
./tools/debug_live.py twitter send 'Hello, world!'

This tool is provided to aid with rapid feedback of changes made to the
friends source tree, and as such is designed to be run from the same directory
that contains 'setup.py'.

It is not intended for use with an installed friends package.
"""

import sys
import logging

sys.path.insert(0, '.')

# Ignore system-installed schema.
from friends.tests.mocks import SCHEMA

from gi.repository import GLib
from friends.utils.logging import initialize

# Print all logs for debugging purposes
initialize(debug=True, console=True)

from friends.service.dispatcher import ManageTimers
from friends.utils.account import find_accounts
from friends.utils.base import initialize_caches, _OperationThread
from friends.utils.model import Model


log = logging.getLogger('friends.debug_live')


loop = GLib.MainLoop()


def row_added(model, itr):
    row = model.get_row(itr)
    print(row)
    log.info('ROWS: {}'.format(len(model)))
    print()


def setup(model, signal, protocol, args):
    _OperationThread.shutdown = loop.quit

    initialize_caches()

    Model.connect('row-added', row_added)

    found = False
    for account in find_accounts().values():
        if account.protocol._name == protocol.lower():
            found = True
            with ManageTimers() as cm:
                account.protocol(*args)

    if not found:
        log.error('No {} found in Ubuntu Online Accounts!'.format(protocol))
        loop.quit()


if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.exit(__doc__)

    protocol = sys.argv[1]
    args = sys.argv[2:]

    ManageTimers.callback = loop.quit
    ManageTimers.timeout = 5
    Model.connect('notify::synchronized', setup, protocol, args)
    loop.run()
