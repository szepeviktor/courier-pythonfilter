#!/usr/bin/python
# auto_whitelist -- Courier filter whitelisting recipients of "local" mail
# Copyright (C) 2006  Gordon Messmer <gordon@dragonsdawn.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import anydbm
import md5
import sys
import re
import string
import thread
import time
import courier.control
import courier.config


# Keep a dictionary of sender/recipient pairs that we've seen before
_whitelistLock = thread.allocate_lock()
_sendersDir = '/var/state/pythonfilter'
try:
    _whitelist = anydbm.open(_sendersDir + '/auto_whitelist', 'c')
except:
    sys.stderr.write('Failed to open correspondents db in %s, make sure that the directory exists\n' % _sendersDir)
    sys.exit(1)

# The good/bad senders lists will be scrubbed at the interval indicated
# in seconds.  All records older than the "_whitelistTTL" number of seconds
# will be removed from the lists.
_whitelistLastPurged = 0
_whitelistTTL = 60 * 60 * 24 * 30
_whitelistPurgeInterval = 60 * 60 * 12

# The hostname will appear in the Received header
_hostname = courier.config.me()

_auth_regex = re.compile(r'\(AUTH: \w* \w*([^)]*)\)\s*by %s' % _hostname)

# Record in the system log that this filter was initialized.
sys.stderr.write('Initialized the "auto_whitelist" python filter\n')


def _lockDB():
    _whitelistLock.acquire()


def _unlockDB():
    # Synchronize the database to disk if the db type supports that
    try:
        _whitelist.sync()
    except AttributeError:
        # this dbm library doesn't support the sync() method
        pass
    _whitelistLock.release()


def checkHeader(header):
    """Search header for _auth_regex.

    If the header is not a "Received" header, return None to indicate
    that scanning should continue.

    If the header is a "Received" header and does not match the regex,
    return 0 to indicate that the filter should stop processing
    headers.

    If the header is a "Received" header and matches the regex, return
    1 to indicate that the filter should whitelist this message.

    """
    if header[:9] != 'Received:':
        return None
    found = _auth_regex.search(header)
    if found:
        return 1
    else:
        return 0


def doFilter(bodyFile, controlFileList):
    """Return a 200 code if the message looks like a reply to a message
    sent by an authenticated user.
    
    First, determine if the sender was authenticated.  If so, record the
    sender/recipient pair.  If not, then check to see if this 
    sender/recipient pair was previously whitelisted.

    """

    global _whitelistLastPurged

    # Scrub the lists if it is time to do so.
    _lockDB()
    if time.time() > (_whitelistLastPurged + _whitelistPurgeInterval):
        minAge = time.time() - _whitelistTTL
        for key in _whitelist.keys():
            if float(_whitelist[key]) < minAge:
                del _whitelist[key]
        _whitelistLastPurged = time.time()
    _unlockDB()

    try:
        bfStream = open(bodyFile)
    except:
        return '451 Internal failure locating message data file'

    header = bfStream.readline()
    while 1:
        buffer = bfStream.readline()
        if buffer == '\n' or buffer == '':
            # There are no more headers.  Scan the header we've got and quit.
            auth = checkHeader(header)
            break
        if buffer[0] in string.whitespace:
            # This is a continuation line.  Add buffer to header and loop.
            header += buffer
        else:
            # This line begins a new header.  Check the previous header and
            # replace it before looping.
            auth = checkHeader(header)
            if auth != None:
                break
            else:
                header = buffer

    if auth == 1:
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
    if not sys.argv[1:]:
        print 'Use:  auto_whitelist.py <control file>'
        sys.exit(1)
    print doFilter('', sys.argv[1:])
