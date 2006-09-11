#!/usr/bin/python
# whitelist_auth -- Courier filter which exempts authenticated users from filtering
# Copyright (C) 2004  Gordon Messmer <gordon@dragonsdawn.net>
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

import courier.config
import re
import string
import sys


# The hostname will appear in the Received header
_hostname = courier.config.me()

_auth_regex = re.compile(r'\(AUTH: \w* \w*([^)]*)\)\s*by %s' % _hostname)

# Record in the system log that this filter was initialized.
sys.stderr.write('Initialized the "whitelist_auth" python filter\n')


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
    """Return a 200 code if the sender appears to have authenticated.

    Courier does not currently contain this information in its control
    files, so we look at the first Received header.  The first one
    should always have come from Courier, and be trusted information.

    After returning a 200 code, the pythonfilter process will
    discontinue further filter processing.

    """

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
        return '200 Ok'
    else:
        # Return no decision for everyone else.
        return ''


if __name__ == '__main__':
    # For debugging, you can create a file that contains a message,
    # including the headers.
    # Run this script with the name of that file as an argument,
    # and it'll print either "200 Ok" to indicate that the sender
    # is whitelisted, or nothing to indicate that the remaining
    # filters would be run.
    if not sys.argv[1:]:
        print 'Use:  whitelist_auth.py <control file>'
        sys.exit(1)
    print doFilter(sys.argv[1], [])
