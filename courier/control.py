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


def getLines(controlFileList, key, maxLines=0):
    """Return a list of values in the controlFileList matching key.

    "key" should be a one character string.  See the "Control Records"
    section of Courier's Mail Queue documentation for a list of valid
    control record keys.

    If the "maxLines" argument is given, it must be a number greater
    than zero.  No more values than indicated by this argument will
    be returned.

    """
    lines = []
    for cf in controlFileList:
        cfo = open(cf)
        ctlLine = cfo.readline()
        while ctlLine:
            if ctlLine[0] == key:
                lines.append(ctlLine[1:])
                if maxLines and len(lines) == maxLines:
                    break
            ctlLine = cfo.readline()
        if maxLines and len(lines) == maxLines:
            break
    lines = map(string.strip, lines)
    return lines


def getSendersMta(controlFileList):
    """Return the "Received-From-MTA" record.

    Courier's documentation indicates that this specifies what goes
    into this header for DSNs generated due to this message.

    """
    senderLines = getLines(controlFileList, 'f', 1)
    if senderLines:
        return senderLines[0]
    else:
        return None


_sender_ipv4_re = re.compile('\[(?:::ffff:)?(\d*.\d*.\d*.\d*)\]')
_sender_ipv6_re = re.compile('\[([0-9a-f:]*)\]')
def getSendersIP(controlFileList):
    """Return an IP address if one is found in the "Received-From-MTA" record."""
    sender = getSendersMta(controlFileList)
    if not sender:
        return sender
    rematch = _sender_ipv4_re.search(sender)
    if rematch.group(1):
        return rematch.group(1)
    # else, we probably have an IPv6 address
    rematch = _sender_ipv6_re.search(sender)
    return rematch.group(1)


def getSender(controlFileList):
    """Return the envelope sender."""
    senderLines = getLines(controlFileList, 's', 1)
    if senderLines:
        return senderLines[0]
    else:
        return None


def getRecipients(controlFileList):
    """Return a list of message recipients.

    This list contains addresses in canonical format, after Courier's
    address rewriting and alias expansion.

    """
    return getLines(controlFileList, 'r')


def getRecipientsData(controlFileList):
    """Return a list of lists with details about message recipients.

    Each list will in the list returned will have the following elements:
    0: The rewritten address
    1: The "original message recipient", as defined by RFC1891
    3: Zero or more characters indicating DSN behavior.

    """
    def _addr(recipients, r):
        if r and r[0]:
            r = map(string.strip, r)
            recipients.append(r)
    recipients = []
    for cf in controlFileList:
        cfo = open(cf)
        r = ['', '', ''] # This list will contain the recipient data.
        ctlLine = cfo.readline()
        while ctlLine:
            if ctlLine[0] == 'r':
                # This is a new record, append any previous record
                # to the recipient data list.
                _addr(recipients, r)
                r = ['', '', '']
                r[0] = ctlLine[1:]
            if ctlLine[0] == 'R':
                r[1] = ctlLine[1:]
            if ctlLine[0] == 'N':
                r[2] = ctlLine[1:]
            ctlLine = cfo.readline()
        # At EOF, add the last recipient to the list
        _addr(recipients, r)
    return recipients
