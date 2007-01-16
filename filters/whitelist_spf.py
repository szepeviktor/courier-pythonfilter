#!/usr/bin/python
# whitlist_spf -- Courier filter which checks SPF records using the "spf" module
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
#

import sys
import string
import courier.control
import spf


# Record in the system log that this filter was initialized.
sys.stderr.write('Initialized the whitelist_spf python filter\n')


def doFilter(bodyFile, controlFileList):
    """Use the SPF mechanism to whitelist email."""
    try:
        sendersMta = courier.control.getSendersMta(controlFileList)
        sendersIp = courier.control.getSendersIP(controlFileList)
        sender = courier.control.getSender(controlFileList)
    except:
        return '451 Internal failure locating control files'

    # Don't waste time on DSNs.
    if sender == '':
        return ''

    helo = string.split(sendersMta,' ')[1]
    results = spf.check(sendersIp, sender, helo)
    # results are pass,deny,unknown
    (decision, numeric, text) = results
    if decision == 'pass':
        return '200 Ok'
