#!/usr/bin/python
# courier.control -- python module for handling Courier message control files
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

import string
import re


def getLines(controlFile, key):
    """Return a list of values in the controlFile matching key.

    "key" should be a one character string.  See the "Control Records"
    section of Courier's Mail Queue documentation for a list of valid
    control record keys.

    """
    lines = []
    # Search for the recipient records
    controlFile.seek(0)
    ctlLine = controlFile.readline()
    while ctlLine:
        if ctlLine[0] == key:
            lines.append(string.strip(ctlLine[1:]))
        ctlLine = controlFile.readline()
    return lines


def getSendersMta(controlFile):
    # Search for the "received-from-mta" record
    senderLines = getLines(controlFile, 'f')
    if senderLines:
        return senderLines[0]
    else:
        return None


_sender_ipv4_re = re.compile('\[(?:::ffff:)?(\d*.\d*.\d*.\d*)\]')
_sender_ipv6_re = re.compile('\[([0-9a-f:]*)\]')
def getSendersIP(controlFile):
    sender = getSendersMta(controlFile)
    if not sender:
        return sender
    rematch = _sender_ipv4_re.search(sender)
    if rematch.group(1):
        return rematch.group(1)
    # else, we probably have an IPv6 address
    rematch = _sender_ipv6_re.search(sender)
    return rematch.group(1)


def getSender(controlFile):
    senderLines = getLines(controlFile, 's')
    if senderLines:
        return senderLines[0]
    else:
        return None


def getRecipients(controlFile):
    return getLines(controlFile, 'r')
