#!/usr/bin/python
# ratelimit -- Courier filter which limits the rate of messages from any IP
# Copyright (C) 2003-2008  Gordon Messmer <gordon@dragonsdawn.net>
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

import ipaddress
import sys
import thread
import time
import courier.control
import courier.config


# The rate is measured in messages / interval in minutes
maxConnections = 60
interval = 1

# The senders lists will be scrubbed at the interval indicated in
# seconds.  All records older than the "interval" number of minutes
# will be removed from the lists.
sendersPurgeInterval = 60 * 60 * 12

# Throttle based on IPv4 /24 or IPv6 /48 network rather than an
# individual address.
limitNetwork = False

def initFilter():
    courier.config.applyModuleConfig('ratelimit.py', globals())

    # Keep a dictionary of authenticated senders to avoid more work than
    # required.
    global _sendersLock
    global _senders
    global _sendersLastPurged
    _sendersLock = thread.allocate_lock()
    _senders = {}
    _sendersLastPurged    = 0

    # Record in the system log that this filter was initialized.
    sys.stderr.write('Initialized the ratelimit python filter\n')


def doFilter(bodyFile, controlFileList):
    """Track the number of connections from each IP and temporarily fail
    if there have been too many."""

    global _sendersLastPurged

    try:
        sender = courier.control.getSendersIP(controlFileList)
        # limitNetwork might mangle "sender," so save a copy
        esender = sender
    except:
        return '451 Internal failure locating control files'

    if limitNetwork:
        if '.' in sender:
            # For IPv4, use the first three octets
            sender = sender[:sender.rindex('.')]
        else:
            # For IPv6, expand the address and then use the first three hextets
            sender = ipaddress.ip_address(unicode(sender)).exploded[:14]

    _sendersLock.acquire()
    try:
        now = int(time.time() / 60)

        # Scrub the lists if it is time to do so.
        if now > (_sendersLastPurged + (sendersPurgeInterval / 60)):
            minAge = now - interval
            for age in _senders.keys():
                if age < minAge:
                    del _senders[age]
            _sendersLastPurged = now

        # First, add this connection to the bucket:
        if not now in _senders:
            _senders[now] = {}
        if not sender in _senders[now]:
            _senders[now][sender] = 1
        else:
            _senders[now][sender] = _senders[now][sender] + 1

        # Now count the number of connections from this sender
        connections = 0
        for i in range(0, interval):
            if (now - i) in _senders and sender in _senders[now - i]:
                connections = connections + _senders[now - i][sender]

        # If the connection count is higher than the maxConnections setting,
        # return a soft failure.
        if connections > maxConnections:
            status = '421 Too many messages from %s, slow down.' % esender
        else:
            status = ''
    finally:
        _sendersLock.release()

    return status
