#!/usr/bin/python
# courier.xfilter -- python module for modifying messages in the queue
# Copyright (C) 2006-2008  Gordon Messmer <gordon@dragonsdawn.net>
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

import os
import subprocess
import thread
import email
# Compatibility with email version 3:
# http://docs.python.org/lib/email-pkg-history.html
try:
    import email.Generator
    email.generator = email.Generator
except ImportError:
    import email.generator
import courier.control
import courier.config


_envLock = thread.allocate_lock()


class XFilterError(Exception):
    pass


class InitError(XFilterError):
    pass


class XFilter(object):
    """Modify messages in the Courier spool.

    This class will load a specified message from Courier's spool and
    allow you to modify it.  This is implemented by loading the
    message as an email.Message object which will be resubmitted to
    the spool.  If the new message is submitted, the original message
    will be marked completed.  If the new message is not submitted,
    no changes will be made to the original message.

    Arguments:
    filterName -- a name identifying the filter calling this class
    bodyFile -- the same argument given to the doFilter function
    controlFileList -- the same argument given to the doFilter function

    The class will raise xfilter.InitError when instantiated if it
    cannot open the bodyFile or any of the control files.

    After creating an instance of this class, use the getMessage
    method to get the email.Message object created from the bodyFile.
    Make any modifications required using the normal python functions
    usable with that object.

    When modifications are complete, call the XFilter object's submit
    method to insert the new message into the spool.

    Use of this module under Courier < 0.57.1 is no longer supported.

    """
    def __init__(self, filterName, bodyFile, controlFileList):
        try:
            bfStream = open(bodyFile)
        except:
            raise InitError('Internal failure opening message data file')
        try:
            self.message = email.message_from_file(bfStream)
        except Exception, e:
            raise InitError('Internal failure parsing message data file: %s' % str(e))
        # Save the arguments
        self.filterName = filterName
        self.bodyFile = bodyFile
        self.controlFileList = controlFileList
        # Parse the control files and save their data
        self.controlData = courier.control.getControlData(controlFileList)

    def getMessage(self):
        return self.message

    def setMessage(self, message):
        self.message = message

    def getControlData(self):
        return self.controlData

    def submit(self):
        bfo = open(self.bodyFile, 'r+')
        bfo.truncate(0)
        g = email.generator.Generator(bfo, mangle_from_=False)
        g.flatten(self.message)
        # Make sure that the file ends with a newline, or courier
        # will choke on the new message file.
        bfo.seek(-1, 2)
        if bfo.read(1) != '\n':
            bfo.seek(0, 2)
            bfo.write('\n')
        bfo.close()
        return ''


class DummyXFilter(XFilter):
    def submit(self):
        return ''
