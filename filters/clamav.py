#!/usr/bin/python
# clamav -- Courier filter which scans messages with ClamAV
# Copyright (C) 2004  Robert Penz <robert@penz.name>
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

import sys
import pyclamav


# Record in the system log that this filter was initialized.
sys.stderr.write('Initialized the "clamavfilter" python filter\n')


def doFilter(bodyFile, controlFileList):
    # check for viruses
    try:
        avresult = pyclamav.scanthis(clamStream)
    except Exception, e:
        return "554 " + str(e)
    if avresult[0]:
        return "554 %s was detected. Abort!" % avresult[1]
    return ''


if __name__ == '__main__':
    # we only work with 1 parameter
    if len(sys.argv) != 2:
        print "Usage: attachment.py <message_body_file>"
        sys.exit(0)
    print doFilter(sys.argv[1], "")
