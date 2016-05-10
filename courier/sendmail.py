#!/usr/bin/python
# courier.sendmail -- python module for sending messages using Courier
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

import subprocess
import config

def sendmail(from_addr, to_addrs, msg):
    """Send a message using Courier's sendmail application.

    from_addr -- string specifying the envelope sender
    to_addrs -- string specifying a recipient address or list specifying
            multiple addresses
    msg -- string representation of the message
    """
    cmd = ['%s/sendmail' % config.bindir]
    if from_addr:
        cmd.extend(['-f', from_addr])
    if isinstance(to_addrs, str):
        cmd.append(to_addrs)
    else:
        cmd.extend(to_addrs)
    sh = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    sh.stdin.write(msg)
    sh.stdin.close()
    sh.wait()
