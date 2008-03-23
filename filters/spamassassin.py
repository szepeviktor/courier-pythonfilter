#!/usr/bin/python
# spamassassin -- Courier filter which scans messages with spamassassin
# Copyright (C) 2007-2008  Jerome Blion <jerome@hebergement-pro.org>
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

import sys
import commands
import courier.config
 
spamcPath = '/usr/bin/spamc'


def initFilter():
    courier.config.applyModuleConfig('spamassassin.py', globals())
    # Record in the system log that this filter was initialized.
    sys.stderr.write('Initialized the "spamassasinfilter" python filter\n')


def doFilter(bodyFile, controlFileList):
    try:
        cmd = spamcPath + ' -c < ' + bodyFile
        (status,output) = commands.getstatusoutput(cmd)
    except Exception, e:
        return "554 " + str(e)
    if status != 0:
        return '554 Mail rejected - spam detected: '+ output
    return ''


if __name__ == '__main__':
    # we only work with 1 parameter
    if len(sys.argv) != 2:
        print "Usage: spamassassin.py <message body file>"
        sys.exit(0)
    initFilter()
    print doFilter(sys.argv[1], "")
