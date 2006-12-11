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

import md5
import sys
import re
import string
import time
import courier.control
import courier.config
import TtlDb


# The good/bad senders lists will be scrubbed at the interval indicated
# in seconds.  All records older than the "_whitelistTTL" number of seconds
# will be removed from the lists.
_whitelistTTL = 60 * 60 * 24 * 30
_whitelistPurgeInterval = 60 * 60 * 12

# Keep a dictionary of sender/recipient pairs that we've seen before
try:
    _whitelist = TtlDb.TtlDb('auto_whitelist', _whitelistTTL, _whitelistPurgeInterval)
except TtlDb.OpenError, e:
    sys.stderr.write(e.message)
    sys.exit(1)


# The hostname will appear in the Received header
_hostname = courier.config.me()

_auth_regex = re.compile(r'\(AUTH: \w* \w*([^)]*)\)\s*by %s' % _hostname)

# Record in the system log that this filter was initialized.
sys.stderr.write('Initialized the "auto_whitelist" python filter\n')


def _checkHeader(header):
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


def _whitelistRecipients(controlFileList):
    sender = string.lower(courier.control.getSender(controlFileList))
    senderMd5 = md5.new(sender)
    _whitelist.lock()
    for recipient in map(string.lower, courier.control.getRecipients(controlFileList)):
        correspondents = senderMd5.copy()
        correspondents.update(recipient)
        cdigest = correspondents.hexdigest()
        _whitelist[cdigest] = str(time.time())
    _whitelist.unlock()


def _checkWhitelist(controlFileList):
    foundAll = 1
    sender = string.lower(courier.control.getSender(controlFileList))
    _whitelist.lock()
    for recipient in map(string.lower, courier.control.getRecipients(controlFileList)):
        correspondents = md5.new(recipient)
        correspondents.update(sender)
        cdigest = correspondents.hexdigest()
        if not _whitelist.has_key(cdigest):
            foundAll = 0
            break
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

    try:
        bfStream = open(bodyFile)
    except:
        return '451 Internal failure locating message data file'

    auth = 0
    header = bfStream.readline()
    while 1:
        buffer = bfStream.readline()
        if buffer == '\n' or buffer == '':
            # There are no more headers.  Scan the header we've got and quit.
            auth = _checkHeader(header)
            break
        if buffer[0] in string.whitespace:
            # This is a continuation line.  Add buffer to header and loop.
            header += buffer
        else:
            # This line begins a new header.  Check the previous header and
            # replace it before looping.
            auth = _checkHeader(header)
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
    if not len(sys.argv) == 3:
        print 'Use:  auto_whitelist.py <body file> <control file>'
        sys.exit(1)
    print doFilter(sys.argv[1], sys.argv[2:])
