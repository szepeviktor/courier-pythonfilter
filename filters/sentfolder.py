#!/usr/bin/python
# sentfolder -- Copies messages sent by local users back to the sender.
# Copyright (C) 2016  Gordon Messmer <gordon@dragonsdawn.net>
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

import email
import email.utils
import sys
import courier.config
import courier.control
import courier.sendmail


siteid = '69f7dc20-7aef-420b-a8d2-85ea229f97ba'


def initFilter():
    courier.config.applyModuleConfig('sentfolder.py', globals())
    # Record in the system log that this filter was initialized.
    sys.stderr.write('Initialized the "sentfolder" python filter\n')


def doFilter(bodyFile, controlFileList):
    sender = courier.control.getAuthUser(controlFileList, bodyFile)
    if not sender:
        return ''

    if '@' not in sender:
        sender = '%s@%s' % (sender, courier.config.me())
    courier.sendmail.sendmail('', sender, makemsg(bodyFile, controlFileList))

    return ''


def makemsg(bodyFile, controlFileList):
    yield ('X-Deliver-To-Sent-Folder: ' + siteid + '\r\n')

    try:
        bfStream = open(bodyFile)
    except:
        raise InitError('Internal failure opening message data file')
    try:
        msg = email.message_from_file(bfStream)
    except Exception, e:
        raise InitError('Internal failure parsing message data file: %s' % str(e))
    tos = msg.get_all('to', [])
    ccs = msg.get_all('cc', [])
    resent_tos = msg.get_all('resent-to', [])
    resent_ccs = msg.get_all('resent-cc', [])
    all_recipients = [x[1] for x in email.utils.getaddresses(tos + ccs + resent_tos + resent_ccs)]
    bccs = []
    for recipient in courier.control.getRecipientsData(controlFileList):
        if recipient[1]:
            r = recipient[1]
        else:
            r = recipient[0]
        if (r not in all_recipients and
            r not in bccs):
            bccs.append(r)
    if bccs:
        yield ('Bcc: ' + ', '.join(bccs) + '\r\n')

    bfStream = open(bodyFile)
    for line in bfStream: yield line


if __name__ == '__main__':
    if not len(sys.argv) == 2:
        print "Usage: sentfolder.py <body file>"
        sys.exit(1)
    initFilter()
    print doFilter(sys.argv[1], [])
