#!/usr/bin/python
# comeagain -- Courier filter implementing a "greylisting" technique.
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
import string
import thread
import time
import courier.control


# Keep a dictionary of sender/recipient pairs that we've seen before
_sendersLock = thread.allocate_lock()
_sendersDir = '/var/state/pythonfilter'
try:
    _senders = anydbm.open(_sendersDir + '/correspondents', 'c')
except:
    sys.stderr.write('Failed to open correspondents db in %s, make sure that the directory exists\n' % _sendersDir)
    sys.exit(1)

# The good/bad senders lists will be scrubbed at the interval indicated
# in seconds.  All records older than the "_sendersTTL" number of seconds
# will be removed from the lists.
_sendersLastPurged = 0
_sendersTTL = 60 * 60 * 24 * 30
_sendersPurgeInterval = 60 * 60 * 12

# Record in the system log that this filter was initialized.
sys.stderr.write('Initialized the "comeagain" python filter\n')


def doFilter(bodyFile, controlFileList):
    """Return a temporary failure message if this sender hasn't tried to
    deliver mail previously.

    Search through the control files and discover the envelope sender
    and message recipients.  If the sender has written to these
    recipients before, allow the message.  Otherwise, throw a
    temporary failure, and expect the remote MTA to try again.  Many
    spamware sites and viruses will not, preventing these messages
    from getting into the users' mailbox.

    """

    global _sendersLastPurged

    try:
        # The envelope sender will always be the first record in the control
        # files, according to the courier documentation.  Open the first file,
        # read the first line, and if it isn't the sender record, return
        # a failure response.
        ctlfile = open(controlFileList[0])
        ctlline = ctlfile.readline()
    except:
        return '451 Internal failure locating control files'

    if ctlline[0] != 's':
        return '451 Internal failure locating envelope sender record'
    if len(ctlline) == 2:
        # Null sender is allowed as a non-fatal error
        return ''

    sender = string.strip(ctlline[1:])

    # Scrub the lists if it is time to do so.
    _sendersLock.acquire()
    if time.time() > (_sendersLastPurged + _sendersPurgeInterval):
        minAge = time.time() - _sendersTTL
        for key in _senders.keys():
            if float(_senders[key]) < minAge:
                del _senders[key]
        _sendersLastPurged = time.time()
    _sendersLock.release()

    # Create a new MD5 object.  The pairs of sender/recipient will
    # be stored in the db in the form of an MD5 digest.
    senderMd5 = md5.new(sender)

    # Create a digest for each recipient and look it up in the db.
    # Update the timestamp of each pair as we look them up.  If any
    # pair does not exist, we'll have to ask the sender to deliver
    # again.
    foundAll=1
    _sendersLock.acquire()
    for recipient in courier.control.getRecipients(controlFileList):
        correspondents = senderMd5.copy()
        correspondents.update(recipient)
        cdigest = correspondents.hexdigest()
        if not _senders.has_key(cdigest):
            foundAll = 0
        _senders[cdigest] = str(time.time())
    _sendersLock.release()

    if foundAll:
        return ''
    else:
        return('421-Please send the message again.\n'
               '421-This is not an indication of a problem:  We require\n'
               '421-that any new sender retry their delivery as proof that\n'
               '421-they are not spamware or virusware.\n'
               '421 Thank you.')


if __name__ == '__main__':
    # For debugging, you can create a file that contains one line,
    # beginning with an 's' character, followed by an email address
    # and more lines, beginning with an 'r' character, for each
    # recipient.  Run this script with the name of that file as an
    # argument, and it'll validate that email address.
    if not sys.argv[1:]:
        print 'Use:  comeagain.py <control file>'
        sys.exit(1)
    print doFilter('', sys.argv[1:])
