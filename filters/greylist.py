#!/usr/bin/python
# greylist -- Courier filter implementing a "greylisting" technique.
# Copyright (C) 2006  Gordon Messmer <gordon@dragonsdawn.net>
# Copyright (C) 2005  Mickael Marchand <marchand@kde.org>
# Copyright (C) 2006  Georg Lutz <georg-list@georglutz.de>
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
import re


# Enable or disable debug logging.
_doDebug = 0

_sendersLock = thread.allocate_lock()
_sendersDir = '/var/state/pythonfilter'
try:
    # Keep a dictionary of sender/recipient/IP triplets that we've seen before
    _sendersPassed = anydbm.open(_sendersDir + '/greylist_Passed', 'c')
    _sendersNotPassed = anydbm.open(_sendersDir + '/greylist_NotPassed', 'c')
    # messages which include these mail addresses either as sender or recipient
    # should not be greylisted (could be your customer database)
    _whitelistMailAddresses = anydbm.open(_sendersDir + '/greylist_whitelistMailAddresses', 'c')
    # messages which include these domains either in sender or recipient addresses
    # should not be greylisted
    _whitelistDomains = anydbm.open(_sendersDir + '/greylist_whitelistDomains', 'c')
    # messages from these IP addresses should not be greylisted
    _whitelistIPAddresses = anydbm.open(_sendersDir + '/greylist_whitelistIPAddresses', 'c')
except:
    sys.stderr.write('Failed to open greylist db in %s, make sure that the directory exists\n' % _sendersDir)
    sys.exit(1)

# The good/bad senders lists will be scrubbed at the interval indicated,
# in seconds, by the _sendersPurgeInterval setting.  Any triplets which
# haven't successfully passed a message will be purged at the age
# indicated by _sendersNotPassedTTL.  Any triplets which have passed a
# message will be purged at the age indicated by _sendersPassedTTL, and
# will have to prove themselves again.  A triplet must be at as old as 
# _greylistTime to be accepted.
_sendersLastPurged = 0
_sendersPurgeInterval = 60 * 60 * 2
_sendersPassedTTL = 60 * 60 * 24 * 36
_sendersNotPassedTTL = 60 * 60 * 24 
_greylistTime = 300

_IPv4Regex = re.compile('^(\d+\.\d+\.\d+)\.\d+$')


# Record in the system log that this filter was initialized.
sys.stderr.write('Initialized the "greylist" python filter\n')


def _Debug(msg):
    if _doDebug:
        sys.stderr.write(msg + '\n')


def _lockDB():
    _sendersLock.acquire()


def _unlockDB():
    # Synchronize the database to disk if the db type supports that
    try:
        _sendersPassed.sync()
        _sendersNotPassed.sync()
    except AttributeError:
        # this dbm library doesn't support the sync() method
        pass
    _sendersLock.release()


def doFilter(bodyFile, controlFileList):
    """Return a temporary failure message if this sender hasn't tried to
    deliver mail previously.

    Search through the control files and discover the envelope sender
    and message recipients.  If the sender has written to these
    recipients before, allow the message.  Otherwise, throw a
    temporary failure, and expect the remote MTA to try again.  Many
    spamware sites and viruses will not, preventing these messages
    from getting into the users' mailbox.
    
    This strategy is based on the whitepaper at:
    http://projects.puremagic.com/greylisting/whitepaper.html

    """

    global _sendersLastPurged

    sendersIP = courier.control.getSendersIP(controlFileList)
    if _whitelistIPAddresses.has_key(sendersIP):
        _Debug('allowing message from whitelisted IP address %s' % sendersIP)
        return ''

    # Calculate the /24 network
    IPv4Match = _IPv4Regex.match(sendersIP)
    if(IPv4Match == None):
        # IPv6 network calculation isn't handled yet
        sendersIPNetwork = sendersIP
    else:
       sendersIPNetwork = IPv4Match.group(1)

   # Grab the sender from the control files.
    try:
        sender = courier.control.getSender(controlFileList)
    except:
        return '451 Internal failure locating control files'
    if sender == '':
        # Null sender is allowed as a non-fatal error
        return ''
    sender = string.lower(sender)

    # Check the sender's address against the address whitelist.
    if _whitelistMailAddresses.has_key(sender):
        _Debug('allowing message from whitelisted sender address %s' % sender)
        return ''

    # Check the sender's domain against the domain whitelist.
    tmpSplit = string.split(sender,'@')
    if len(tmpSplit) == 2 and _whitelistDomains.has_key(tmpSplit[1]):
        _Debug('allowing message from sender in whitelisted domain %s' % sender)
        return ''

    # Scrub the lists if it is time to do so.
    _lockDB()
    if time.time() > (_sendersLastPurged + _sendersPurgeInterval):
        _Debug('Purging _senders list')
        # Any records created before these two times, respectively, will be removed
        # from the database.
        minAgePassed = time.time() - _sendersPassedTTL
        minAgeNotPassed = time.time() - _sendersNotPassedTTL
        
        for key in _sendersPassed.keys():
            if float(_sendersPassed[key]) < minAgePassed:
                del _sendersPassed[key]
        for key in _sendersNotPassed.keys():
            if float(_sendersNotPassed[key]) < minAgeNotPassed:
                del _sendersNotPassed[key]
        _sendersLastPurged = time.time()
    _unlockDB()

    # Create a new MD5 object.  The sender/recipient/IP triplets will
    # be stored in the db in the form of an MD5 digest.
    senderMd5 = md5.new(sender)

    # Create a digest for each triplet and look it up first in the
    # _sendersNotPassed db.  If it's found there, but is not old 
    # enough to meet _greylistTime, save the minimum amount of time
    # the sender must wait before retrying for the error message that
    # we'll return.  If it is old enough, remove the digest from 
    # _sendersNotPassed db, and save it in the _sendersPassed db.
    # Then, check for the triplet in _sendersPassed db, and update
    # its time value if found.  If the triplet isn't found in the
    # _sendersPassed db, then create a new entry in the
    # _sendersNotPassed db, and save the minimum wait time.
    foundAll = 1
    biggestTimeToGo = 0

    for recipient in courier.control.getRecipients(controlFileList):
        recipient = string.lower(recipient)

        # Check the recipient's address against the address whitelist.
        if _whitelistMailAddresses.has_key(recipient):
            _Debug('allowing message sent to whitelisted recipient address %s' % recipient)
            return ''

        # Check the recipient's domain against the domain whitelist.
        tmpSplit = string.split(recipient,'@')
        if len(tmpSplit) == 2  and _whitelistDomains.has_key(tmpSplit[1]):
            _Debug('allowing message sent to recipient in whitelisted domain %s' % recipient)
            return ''

        correspondents = senderMd5.copy()
        correspondents.update(recipient)
        correspondents.update(sendersIPNetwork)
        cdigest = correspondents.hexdigest()
        _lockDB()
        if _sendersNotPassed.has_key(cdigest):
            _Debug('found triplet in the NotPassed db')
            firstTimestamp = float(_sendersNotPassed[cdigest])
            timeToGo = firstTimestamp + _greylistTime - time.time()
            if timeToGo > 0:
                # The sender needs to wait longer before this delivery is allowed.
                _Debug('triplet in NotPassed db is not old enough')
                foundAll = 0
                if timeToGo > biggestTimeToGo:
                    biggestTimeToGo = timeToGo
            else:
                _Debug('triplet in NotPassed db is now passed')
                _sendersPassed[cdigest] = str(time.time())
                del(_sendersNotPassed[cdigest])
        elif _sendersPassed.has_key(cdigest):
            _Debug('triplet found in the Passed db')
            _sendersPassed[cdigest] = str(time.time())
        else:
            _Debug('new triplet in this message')
            foundAll = 0
            timeToGo = _greylistTime
            if timeToGo > biggestTimeToGo:
                biggestTimeToGo = timeToGo
            _sendersNotPassed[cdigest] = str(time.time())
        _unlockDB()

    if foundAll:
        return ''
    else:
        return('451 4.7.1 Greylisting in action, please come back in %s' % time.strftime("%H:%M:%S", time.gmtime(biggestTimeToGo)))


def _doDumpDb(db):
    if db not in ('MailAddresses', 'Domains', 'IPAddresses'):
        sys.stderr.write('Second argument must be one of: MailAddresses, Domains, IPAddresses\n')
        sys.exit(1)
    try:
        hash = anydbm.open(_sendersDir + '/greylist_whitelist' + db, 'n')
    except:
        sys.stderr.write('Failed to open the %s DB.\n' % db)
        sys.exit(1)
    for key in hash.keys():
        print key + "\t" + hash[key]


def _doImportFile(db, inputFile):
    if db not in ('MailAddresses', 'Domains', 'IPAddresses'):
        sys.stderr.write('Second argument must be one of: MailAddresses, Domains, IPAddresses\n')
        sys.exit(1)
    try:
        hash = anydbm.open(_sendersDir + '/greylist_whitelist' + db, 'n')
    except:
        sys.stderr.write('Failed to open the  %s DB.\n' % db)
        sys.exit(1)
    try:
        ifo = open(inputFile, 'r')
    except:
        sys.stderr.write('Failed to open the given file %s\n' % inputFile)
        sys.exit(1)
    for line in ifo.readlines():
        # strip trailing newline
        line = line.strip()
        pair = line.split('\t', 1)
        if len(pair) == 1:
            hash[pair[0]] = ''
        else:
            hash[pair[0]] = pair[1]


if __name__ == '__main__':
    # For debugging, you can create a file that contains one line,
    # beginning with an 's' character, followed by an email address
    # and more lines, beginning with an 'r' character, for each
    # recipient.  Run this script with the name of that file as an
    # argument, and it'll validate that email address.
    def _printHelp():
        print """Use: greylist.py test <control file>
     greylist.py dump [MailAddresses,Domains,IPAddresses]
     greylist.py import [MailAddresses,Domains,IPAddresses] <whitelist file>
    
"test" will read a file formatted like Courier's control files and 
print out the SMTP response that would be generated by the filter.

"dump" will read the contents of a diven database file and print all
of its key/value pairs.  It can be used to save the contents of one
of the existing DBs so that it can be modified and then imported.

"import" will read the contents of the given file and add
the values listed to the named whitelist DB.  The greylist 
documentation recommends against whitelisting Domains or MailAddresses
because they are easily forged.  Whitelist senders' IPAddresses 
instead.  The Domains and MailAddresses whitelists apply to both
senders and recipients; whitelisting a local user may allow spammers
to use that address as a "sender" to bypass the greylist controls.
It will also bypass the controls for other users if a message is
sent to a whitelisted user and non-whitelisted users.
The import is a destructive operation.  The existing list will be 
replaced.  Make sure that the file that you're importing contains all
of the values that you need.  The filter must not be running during 
an import operation.\n"""
        sys.exit(1)
    if not sys.argv[1:]:
        _printHelp()
    elif sys.argv[1] == 'dump' and len(sys.argv) == 3:
        _doDumpDb(sys.argv[2])
    elif sys.argv[1] == 'import' and len(sys.argv) == 4:
        _doImportFile(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == 'test' and len(sys.argv) >= 3:
        print doFilter('', sys.argv[2:])
    else:
        _printHelp()
