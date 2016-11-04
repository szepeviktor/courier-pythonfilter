#!/usr/bin/python
# attachments -- Courier filter which blocks specified attachment types
# Copyright (C) 2005-2008  Robert Penz <robert@penz.name>
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
import sys
import re
import email.header
import tempfile
import courier.config
try:
    import libarchive
    from cStringIO import StringIO
    haveLibarchive = True
except:
    haveLibarchive = False


blockedPattern = re.compile(r'^.*\.(scr|exe|com|bat|pif|lnk|sys|mid|vb|js|ws|shs|ceo|cmd|cpl|hta|vbs)$', re.I)


def initFilter():
    config = courier.config.getModuleConfig('attachments.py')
    if 'blockedPattern' in config:
        # blockedPattern in configuration file should be only the
        # regular expression.  We recompile it here.
        global blockedPattern
        blockedPattern = re.compile(config['blockedPattern'], re.I)
    # Record in the system log that this filter was initialized.
    sys.stderr.write('Initialized the "attachments" python filter\n')


def checkArchive(filename, part):
    if not haveLibarchive:
        return False
    fparts = filename.split('.')
    if fparts[-1].lower() in libarchive.FILTERS:
        fparts.pop()
    if fparts[-1].lower() not in libarchive.FORMATS:
        return False
    d = tempfile.mkdtemp()
    f = '%s/%s' % (d, filename.replace('/',''))
    t = open(f,'w')
    t.write(part.get_payload(decode=True))
    t.close()
    a = libarchive.Archive(f)
    found = False
    for entry in a:
        if blockedPattern.match(entry.pathname):
            found = True
    os.unlink(f)
    os.rmdir(d)
    return found

def doFilter(bodyFile, controlFileList):
    try:
        msg = email.message_from_file(open(bodyFile))
    except Exception, e:
        return "554 " + str(e)

    for part in msg.walk():
        # multipart/* are just containers
        if part.get_content_maintype() == 'multipart':
            continue

        filename = part.get_filename()
        if not filename:
            continue
        if type(filename) is str:
            dh = email.header.decode_header(filename)
            filename = ''.join([ unicode(t[0], t[1] or default_charset) for t in dh ])

        if checkArchive(filename, part):
            return "554 The extension of the attached file is blacklisted"

        if blockedPattern.match(filename):
            return "554 The extension of the attached file is blacklisted"

    return ''


if __name__ == '__main__':
    # For debugging, you can create a file that contains a message
    # body, possibly including attachments.
    # Run this script with the name of that file as an argument,
    # and it'll print either a permanent failure code to indicate
    # that the message would be rejected, or print nothing to
    # indicate that the remaining filters would be run.
    if len(sys.argv) != 2:
        print "Usage: attachments.py <message_body_file>"
        sys.exit(0)
    initFilter()
    print doFilter(sys.argv[1], [])
