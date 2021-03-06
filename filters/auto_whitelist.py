#!/usr/bin/python
# auto_whitelist -- Courier filter whitelisting recipients of "local" mail
# Copyright (C) 2006-2008  Gordon Messmer <gordon@dragonsdawn.net>
#
# This file is part of pythonfilter.
#
# pythonfilter is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pythonfilter is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pythonfilter.  If not, see <http://www.gnu.org/licenses/>.

import hashlib
import sys
import time
import courier.config
import courier.control
import TtlDb


# The good/bad senders lists will be scrubbed at the interval indicated
# in seconds.  All records older than the "whitelistTTL" number of seconds
# will be removed from the lists.
whitelistTTL = 60 * 60 * 24 * 30
whitelistPurgeInterval = 60 * 60 * 12


def initFilter():
    courier.config.applyModuleConfig('auto_whitelist.py', globals())
    # Keep a dictionary of sender/recipient pairs that we've seen before
    try:
        global _whitelist
        _whitelist = TtlDb.TtlDb('auto_whitelist', whitelistTTL, whitelistPurgeInterval)
    except TtlDb.OpenError, e:
        sys.stderr.write('Could not open auto_whitelist TtlDb: %s\n' % e)
        sys.exit(1)
    # Record in the system log that this filter was initialized.
    sys.stderr.write('Initialized the "auto_whitelist" python filter\n')


def _whitelistRecipients(controlFileList):
    sender = courier.control.getSender(controlFileList).lower()
    senderMd5 = hashlib.md5(sender)
    _whitelist.lock()
    try:
        for recipient in courier.control.getRecipients(controlFileList):
            recipient = recipient.lower()
            # Don't allow a whitelist between identical addresses.  Users
            # sometimes email themselves a note, which creates a path for
            # spam.
            if recipient == sender:
                continue
            correspondents = senderMd5.copy()
            correspondents.update(recipient)
            cdigest = correspondents.hexdigest()
            _whitelist[cdigest] = time.time()
    finally:
        _whitelist.unlock()


def _checkWhitelist(controlFileList):
    foundAll = 1
    sender = courier.control.getSender(controlFileList).lower()
    _whitelist.lock()
    try:
        for recipient in courier.control.getRecipients(controlFileList):
            correspondents = hashlib.md5(recipient.lower())
            correspondents.update(sender)
            cdigest = correspondents.hexdigest()
            if not cdigest in _whitelist:
                foundAll = 0
                break
    finally:
        _whitelist.unlock()
    return foundAll


def doFilter(bodyFile, controlFileList):
    """Return a 200 code if the message looks like a reply to a message
    sent by an authenticated user.

    First, determine if the sender was authenticated.  If so, record the
    sender/recipient pair.  If not, then check to see if this
    sender/recipient pair was previously whitelisted.

    """

    _whitelist.purge()
    authUser = courier.control.getAuthUser(controlFileList, bodyFile)
    if authUser:
        _whitelistRecipients(controlFileList)
        return ''
    else:
        if _checkWhitelist(controlFileList):
            return '200 Ok'
        else:
            # Return no decision for everyone else.
            return ''


if __name__ == '__main__':
    # For debugging, you can create a file that contains one line,
    # beginning with an 's' character, followed by an email address
    # and more lines, beginning with an 'r' character, for each
    # recipient.  Run this script with the name of that file as an
    # argument, and it'll validate that email address.
    if not len(sys.argv) == 3:
        print 'Use:  auto_whitelist.py <body file> <control file>'
        sys.exit(1)
    initFilter()
    print doFilter(sys.argv[1], sys.argv[2:])
