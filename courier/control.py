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

import re
import string
import time


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
    2: Zero or more characters indicating DSN behavior.

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


def addRecipient(controlFileList, recipient):
    """Add a recipient to a controlFileList set.

    The recipient argument must contain a canonical address.  Local
    aliases are not allowed.

    """
    recipientData = [recipient, '', '']
    addRecipientData(controlFileList, recipientData)


def addRecipientData(controlFileList, recipientData):
    """Add a recipient to a controlFileList set.

    The recipientData argument must contain the same information that
    is normally returned by the getRecipientsData function for each
    recipient.  Recipients should be added one at a time.

    """
    # FIXME:  How strict is courier about its upper limit of
    # recipients per control file?  It's easiest to append the
    # recipient to the last control file, but it would be more
    # robust to check the number of recipients in it first and
    # create a new file if necessary.
    if len(recipientData) != 3:
        raise ValueError, 'recipientData must be a list of 3 values.'
    cf = controlFileList[-1]
    cfo = open(cf, 'a')
    cfo.write('r%s\n' % recipientData[0])
    cfo.write('R%s\n' % recipientData[1])
    cfo.write('N%s\n' % recipientData[2])
    cfo.close()


def delRecipient(controlFileList, recipient):
    """Remove a recipient from the list.

    The recipient arg is a canonical address found in one of the
    control files in controlFileList.

    The first recipient in the controlFileList that exactly matches
    the address given will be removed by way of marking that delivery
    complete, successfully.

    You should log all such removals so that messages are never
    silently lost.

    """
    def _markComplete(controlFile, recipientIndex):
        cfo = open(controlFile, 'a')
        cfo.seek(0, 2) # Seek to the end of the file
        cfo.write('I%d R Ok - Removed by courier.control.py\n' %
                  recipientIndex)
        cfo.write('S%d %d\n' % (recipientIndex, int(time.time())))
    for cf in controlFileList:
        ri = 0 # Recipient index for this file
        rcpts = getRecipients([cf])
        for x in rcpts:
            if x == recipient:
                _markComplete(cf, ri)
                return
            ri += 1


def delRecipientData(controlFileList, recipientData):
    """Remove a recipient from the list.

    The recipientData arg is a list similar to the data returned by
    getRecipientsData found in one of the control files in
    controlFileList.

    The first recipient in the controlFileList that exactly matches
    the data given will be removed by way of marking that delivery
    complete, successfully.

    You should log all such removals so that messages are never
    silently lost.

    """
    def _markComplete(controlFile, recipientIndex):
        cfo = open(controlFile, 'a')
        cfo.seek(0, 2) # Seek to the end of the file
        cfo.write('I%d R Ok - Removed by courier.control.py\n' %
                  recipientIndex)
        cfo.write('S%d %d\n' % (recipientIndex, int(time.time())))
    if len(recipientData) != 3:
        raise ValueError, 'recipientData must be a list of 3 values.'
    for cf in controlFileList:
        ri = 0 # Recipient index for this file
        rcpts = getRecipientsData([cf])
        for x in rcpts:
            if x == recipientData:
                _markComplete(cf, ri)
                return
            ri += 1
