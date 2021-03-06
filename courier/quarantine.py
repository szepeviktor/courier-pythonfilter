#!/usr/bin/python
# courier.quarantine -- python module for quarantining and releasing messages
# Copyright (C) 2008  Gordon Messmer <gordon@dragonsdawn.net>
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

import anydbm
import datetime
import email
import fcntl
import os
import time
import cPickle as pickle
import courier.config
import courier.control
import courier.sendmail
import courier.xfilter


# Defaults:
config = {'siteid': 'local',
          'dir': '/var/lib/pythonfilter/quarantine',
          'days': 14,
          'default': 1}


def init():
    global config
    # Load the configuration if it has not already been loaded.
    if 'default' in config:
        config = courier.config.getModuleConfig('Quarantine')


def _getDb():
    """Return the dbm and lock file handles."""
    dbmfile = '%s/msgs.db' % config['dir']
    lockfile = '%s/msgs.lock' % config['dir']
    lock = open(lockfile, 'w')
    fcntl.flock(lock, fcntl.LOCK_EX)
    dbm = anydbm.open(dbmfile, 'c')
    return(dbm, lock)


def _closeDb(dbm, lock):
    """Unlock and close the lock and dbm files"""
    fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
    lock.close()
    dbm.close()


def _copyFile(source, destination):
    dfile = open(destination, 'w')
    sfile = open(source, 'r')
    dfile.write(sfile.read())


def sendNotice(message, address, sender=None):
    if not sender:
        sender = 'postmaster@%s' % courier.config.me()
    msg = ('From: Mail Quarantine System <%s>\r\n'
           'To: <%s>\r\n'
           'Subject: Quarantine notice\r\n\r\n'
           '%s'
           % (sender, address, message))
    # Send the recipient a notice if notifyRecipient isn't
    # available, or if it is present and a true value.
    rcpts = []
    if('notifyRecipient' not in config
       or config['notifyRecipient']):
        rcpts.append(address)
    if 'alsoNotify' in config and config['alsoNotify']:
        rcpts.append(config['alsoNotifiy'])
    if rcpts:
        courier.sendmail.sendmail('', rcpts, msg)


def sendFailureNotice(requestedId, address):
    message = """The quarantine system received a request from your address
to release the message with id '%s' from the quarantine.  That message
was not found.  It may have already expired.

I'm sorry that it didn't work out.  Please contact your system admin
for further assistance.
""" % requestedId
    sendNotice(message, address)


def quarantine(bodyFile, controlFileList, explanation):
    # Generate an ID for this quarantined message.  The ID will consist
    # of the inode number for the body file.  The inode number from the
    # original body file will be used for the temporary file's name.
    obodyinfo = os.stat(bodyFile)
    bodypath = '%s/tmp.%s' % (config['dir'], obodyinfo.st_ino)
    body = open(bodypath, 'w')
    bodyinfo = os.fstat(body.fileno())
    body.close()
    msgid = bodyinfo.st_ino
    # Copy files to quarantine
    quarantinePaths = ('%s/D%s' % (config['dir'], msgid), [])
    os.rename(bodypath, quarantinePaths[0])
    ctlFileExt = ''
    ctlFileNum = 0
    _copyFile(bodyFile, quarantinePaths[0])
    for x in controlFileList:
        ctlFilePath = '%s/C%s%s' % (config['dir'], msgid, ctlFileExt)
        ctlFileNum += 1
        ctlFileExt = '.%s' % ctlFileNum
        _copyFile(x, ctlFilePath)
        quarantinePaths[1].append(ctlFilePath)
    # Open and lock the quarantine DB
    (dbm, lock) = _getDb()
    # Record this set of files in the DB
    dbm['%d' % msgid] = pickle.dumps((time.time(), quarantinePaths))
    # Unlock the DB
    _closeDb(dbm, lock)
    # Prepare notice for recipients of quarantined message
    # Some sites would prefer that only admins release messages from the
    # quarantine.
    if('userRelease' in config
       and config['userRelease'] == 0
       and 'alsoNotify' in config
       and config['alsoNotify']):
        release = config['alsoNotify']
    else:
        release = 'quarantine-%s-%s@%s' % (config['siteid'],
                                           msgid,
                                           courier.config.me())
    days = config['days']
    expiration = datetime.date.fromtimestamp(time.time() + (days * 86400)).strftime('%a %B %d, %Y')
    # Parse the message for its sender and subject:
    try:
        bfStream = open(bodyFile)
    except:
        raise #InitError('Internal failure opening message data file')
    try:
        qmessage = email.message_from_file(bfStream)
    except Exception, e:
        # TODO: Handle this error.
        raise #InitError('Internal failure parsing message data file: %s' % str(e))
    qmessageSender = qmessage['from']
    qmessageSubject = qmessage['subject']
    message = """You received a message that was quarantined because:
%s

This message will be held in the quarantine until %s.
After that time, it will no longer be possible to release the message.

The message appears to have come from %s, although
this address could have been forged and should not be trusted.  The
message subject was "%s".

If this was a message that you were expecting, and you know that it
is safe to continue, then forward this message to the following address
to release the quarantined message.  If you do not recognise the
sender, or were not expecting this message, then releasing it from
the quarantine could be very harmful.  You will almost always want
to simply ignore this notice.

Quarantine release address:
%s
    """ % (explanation,
           expiration,
           qmessageSender,
           qmessageSubject,
           release)
    # Mark recipients complete and send notices.
    controlData = courier.control.getControlData(controlFileList)
    for x in controlData['r']:
        courier.control.delRecipientData(controlFileList, x)
        sendNotice(message, x[0])


def release(requestedId, address):
    # Open and lock the quarantine DB
    (dbm, lock) = _getDb()
    if requestedId in dbm:
        quarantinePaths = pickle.loads(dbm[requestedId])[1]
    else:
        quarantinePaths = None
    # Unlock the DB
    _closeDb(dbm, lock)
    # If quarantinePaths is None, then an invalid ID was requested.
    if not quarantinePaths:
        # Alert the user that his request failed
        sendFailureNotice(requestedId, address)
        return
    for x in courier.control.getControlData(quarantinePaths[1])['r']:
        if(x[0] == address or
           x[1] == address or
           x[1] == '%s%s' % ('rfc822;', address)):
            courier.sendmail.sendmail('', address, quarantinePaths[0].read())
            return
    # If no address matched, alert the user that the request was invalid.
    sendFailureNotice(requestedId, address)


def purge():
    # Open and lock the quarantine DB
    (dbm, lock) = _getDb()
    minVal = time.time() - (int(config['days']) * 86400)
    for x in dbm.keys():
        (qtime, quarantinePaths) = pickle.loads(dbm[x])
        if qtime < minVal:
            # Files may have been removed for some reason, don't treat
            # that as a fatal condition.
            try:
                os.remove(quarantinePaths[0])
            except:
                pass
            for p in quarantinePaths[1]:
                try:
                    os.remove(p)
                except:
                    pass
            del dbm[x]
    # Unlock the DB
    _closeDb(dbm, lock)
