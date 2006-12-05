#!/usr/bin/python
# dialback -- Courier filter which verifies sender addresses by contacting their MX
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

import DNS
import anydbm
import os
import select
import smtplib
import socket
import string
import sys
import thread
import time
import courier.config


# Keep a dictionary of authenticated senders to avoid more work than
# required.
_sendersLock = thread.allocate_lock()
_sendersDir = '/var/state/pythonfilter'
try:
    _goodSenders = anydbm.open(_sendersDir + '/goodsenders', 'c')
    _badSenders = anydbm.open(_sendersDir + '/badsenders', 'c')
except:
    sys.stderr.write('Failed to open db in %s, make sure that it exists\n' % _sendersDir)
    sys.exit(1)

# The good/bad senders lists will be scrubbed at the interval indicated
# in seconds.  All records older than the "TTL" number of seconds
# will be removed from the lists.
_sendersLastPurged = 0
_sendersTTL = 60 * 60 * 24 * 7
_sendersPurgeInterval = 60 * 60 * 12

# SMTP conversation timeout in seconds.  Setting this too low will
# lead to 4XX failures.
_smtpTimeout = 60

# Initialize the DNS module
DNS.DiscoverNameServers()

# The postmaster address will be used for the "MAIL" command in the
# dialback conversation.
postmasterAddr = 'postmaster@%s' % courier.config.me()

# Record in the system log that this filter was initialized.
sys.stderr.write('Initialized the dialback python filter\n')


def _lockDB():
    _sendersLock.acquire()


def _unlockDB():
    # Synchronize the database to disk if the db type supports that
    try:
        _goodSenders.sync()
        _badSenders.sync()
    except AttributeError:
        # this dbm library doesn't support the sync() method
        pass
    _sendersLock.release()


def doFilter(bodyFile, controlFileList):
    """Contact the MX for this message's sender and validate their address.

    Validation will be done by starting an SMTP session with the MX and
    checking the server's reply to a RCPT command with the sender's address.

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

    # If this sender is known already, then we don't actually need to do the
    # dialback.  Update the timestamp in the dictionary and then return the
    # status.
    _lockDB()
    # Scrub the lists if it is time to do so.
    if time.time() > (_sendersLastPurged + _sendersPurgeInterval):
        minAge = time.time() - _sendersTTL
        for key in _goodSenders.keys():
            if float(_goodSenders[key]) < minAge:
                del _goodSenders[key]
        for key in _badSenders.keys():
            if float(_badSenders[key]) < minAge:
                del _badSenders[key]
        _sendersLastPurged = time.time()
    if _goodSenders.has_key(sender):
        _goodSenders[sender] = str(time.time())
        _unlockDB()
        return ''
    if _badSenders.has_key(sender):
        _badSenders[sender] = str(time.time())
        _unlockDB()
        return '517 Sender does not exist: %s' % sender
    _unlockDB()

    # The sender is new, so break the address into name and domain parts.
    try:
        (senderName, senderDomain) = string.split(sender , '@')
    except:
        # Pretty sure this can't happen...
        return '501 Envelope sender is invalid'

    # Look up the MX records for this sender's domain in DNS.  If none are
    # found, then check the domain for an A record, and dial back to that
    # host.  If no A record is found, then perhaps the message is a DSN...
    # Just return a success code if no MX and no A records are found.
    try:
        mxList = DNS.mxlookup(senderDomain)
        if mxList == []:
            if socket.getaddrinfo(senderDomain, 'smtp'):
                # put this host in the mxList and continue
                mxList.append((1, senderDomain))
            else:
                # no record was found
                return ''
    except:
        # Probably a DNS timeout...
        # Also should never happen, because courier's smtpd should have
        # just validated this domain.
        return '421 DNS failure resolving %s' % senderDomain

    # Loop through the dial-back candidates and ask each one to validate
    # the address that we got as the sender.  If they return a success
    # code to the RCPT command, then we accept the mail.  If they return
    # any 5XX code, we refuse the incoming mail with a 5XX error, as well.
    # If no SMTP server is available, or all report 4XX errors, we'll
    # give a 4XX error to the sender.

    # Unless we get a satisfactory responce from a server, we'll use
    # this as the filer status.
    filterReply = '421 No SMTP servers were available to authenticate sender'

    # Create a pipe so that we can read the results of the
    # test from the dialback thread.
    (rpipe, wpipe) = os.pipe()

    for MX in mxList:
        # Create an SMTP instance.  If the dialback thread takes
        # too long, we'll close its socket.
        smtpi = smtplib.SMTP()
        # Run the dialback in another thread, and wait for a
        # reply.
        thread.start_new_thread(dialback, (smtpi, MX, sender, wpipe))

        readyPipe = select.select([rpipe],[],[], _smtpTimeout)
        if rpipe not in readyPipe[0]:
            # Time to cancel this SMTP conversation
            smtpi.close()
            # The dialback thread will now write a failure message to
            # its status pipe, and we'll need to clear that out.
            os.read(rpipe, 1024)
            continue

        status = os.read(rpipe, 1024)
        if len(status) < 4:
            # not a full status message
            continue
        if status[:3] == '250':
            # Success!  Mark this user good.
            _lockDB()
            _goodSenders[sender] = str(time.time())
            _unlockDB()
            filterReply = ''
        if status[0] == '5':
            # Mark this user bad.
            _lockDB()
            _badSenders[sender] = str(time.time())
            _unlockDB()
            filterReply = '517-MX server %s said:\n' \
                          '517 Sender does not exist: %s' % (MX[1], sender)

    os.close(rpipe)
    os.close(wpipe)
    return filterReply


def dialback(SMTP, MX, sender, statusPipe):
    try:
        SMTP.connect(MX[1])
        (code, reply) = SMTP.helo()
        if code // 100 != 2:
            sys.stderr.write('%s rejected the HELO command' % MX[1])
            os.write(statusPipe, '%d %s' % (code, reply))
            return

        (code, reply) = SMTP.mail(postmasterAddr)
        if code // 100 != 2:
            sys.stderr.write('%s rejected the MAIL FROM command' % MX[1])
            os.write(statusPipe, '%d %s' % (code, reply))
            return

        (code, reply) = SMTP.rcpt(sender)
        SMTP.quit()
    except:
        code = 400
        reply = 'SMTP class exception'

    # Write the status of the RCPT command back to the caller,
    # and let it be handled there.
    os.write(statusPipe, '%d %s' % (code, reply))


if __name__ == '__main__':
    # For debugging, you can create a file that contains just one
    # line, beginning with an 's' character, followed by an email
    # address.  Run this script with the name of that file as an
    # argument, and it'll validate that email address.
    if not sys.argv[1:]:
        print 'Use:  dialback.py <control file>'
        sys.exit(1)
    print doFilter('', sys.argv[1:])
