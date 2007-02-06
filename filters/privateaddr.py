#!/usr/bin/python
# privateaddr -- Courier filter which grants selective access to some addresses
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

import string
import sys
import re
import courier.config
import courier.control


# _private_rcpts is a list of addresses which should only accept
# mail from listed senders.  The key name should be the private
# address; the value should be a list of regexes which match
# approved senders.
_private_rcpts = { 'help@ee.washington.edu': ['[^@]*@.*washington.edu'],
                   'webmaster@ee.washington.edu': ['[^@]*@.*washington.edu'],
                   'msdn@ee.washington.edu': ['[^@]*@.*washington.edu'],
                   'researchhelp@ee.washington.edu': ['[^@]*@.*washington.edu'],
                   'desktophelp@ee.washington.edu': ['[^@]*@.*washington.edu'],
                   'securityhelp@ee.washington.edu': ['[^@]*@.*washington.edu'],
                   'gnlhelp@ee.washington.edu': ['[^@]*@.*washington.edu'],
                   'memshelp@ee.washington.edu': ['[^@]*@.*washington.edu'],
                   'compstudenthelp@ee.washington.edu': ['[^@]*@.*washington.edu'] }


# Avoid recompiling REs on each run by compiling them here:
_private_re = {}
for x in _private_rcpts.keys():
    for y in _private_rcpts[x]:
        _private_re[y] = re.compile(y)


# Record in the system log that this filter was initialized.
sys.stderr.write('Initialized the "privateaddr" python filter\n')


def doFilter(bodyFile, controlFileList):
    """Refuse mail if recipient is private, and sender is not approved."""
    for addr in courier.control.getRecipientsData(controlFileList):
        if addr[1]:
            if(addr[1][:7] == 'rfc822;'):
                rcpt = addr[1][7:]
            else:
                rcpt = addr[1]
        else:
                rcpt = addr[0]
        if courier.config.locallowercase():
            rcpt = string.lower(rcpt)
        if _private_rcpts.has_key(rcpt):
            senderAllowed = 0
            sender = courier.control.getSender(controlFileList)
            for pattern in _private_rcpts[rcpt]:
                if _private_re[pattern].match(sender):
                    senderAllowed = 1
            if senderAllowed == 0:
                sys.stderr.write('Message to %s from %s refused by privateaddr.py\n' % 
                                 (rcpt, sender) )
                return '517 Sender is not allowed by privacy settings.'
    return ''
