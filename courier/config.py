#!/usr/bin/python
# courier.config -- python module for Courier configuration access
# Copyright (C) 2004  Gordon Messmer <gordon@dragonsdawn.net>
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
import anydbm
import string
import socket


sysconf = '/etc/courier'
prefix  = '/usr/lib/courier'
spool   = '/var/spool/courier'


def read1line(file):
    try:
        cfile = open(sysconf + '/' + file, 'r')
    except IOError:
        return None
    return string.strip(cfile.readline())


def me(_cached = [None]):
    """Return Courier's "me" value.

    Call this function with no arguments.

    """
    # check the cache to see if "me" has been looked up already
    # next look at the "me" config file
    # otherwise use the value of gethostname()
    if _cached[0]:
        return _cached[0]
    val = read1line('me')
    if val:
        _cached[0] = val
        return val
    val = socket.gethostname()
    _cached[0] = val
    return val


def smtpaccess(ip):
    """ Return the courier smtpaccess value associated with the IP address."""
    # First break the IP address into parts, either IPv4 or IPv6
    if '.' in  ip:
        ipsep = '.'
    elif ':' in ip:
        ipsep = ':'
    else:
        sys.stderr.write('Couldn\'t break %s into parts' % ip)
        return None
    # Next, open the smtpaccess database for ip lookups
    try:
        smtpdb = anydbm.open(sysconf + '/smtpaccess.dat', 'r')
    except:
        sys.stderr.write('Couldn\'t open smtpaccess.dat in ' + sysconf)
        return None
    # Search for a match, most specific to least, and return the
    # first match.
    while ip:
        if smtpdb.has_key(ip):
            return smtpdb[ip]
        # if the ip doesn't match yet, strip off another part
        try:
            ri = string.rindex(ip, ipsep)
            ip = ip[:ri]
        except:
            # separator wasn't found, we don't need to search any more
            return None


def getSmtpaccessVal(key, ip):
    """Return a string from the smtpaccess database.

    The value returned will be None if the IP is not found in the
    database, or if the database value doesn\'t contain the key
    argument.

    The value returned will be '' if the IP is found, and database
    value contains the key, but the key's value is empty.

    Otherwise, the value returned will be a string.

    """
    dbval = smtpaccess(ip)
    if dbval is None:
        return None
    keyeqlen = len(key) + 1
    keyeq = key + '='
    dbvals = string.split(dbval, ',')
    for val in dbvals:
        if val == key:
            # This item in the db matches the key, but has no
            # associated value.
            return ''
        if val[:keyeqlen] == keyeq:
            val = val[keyeqlen:]
            return val


def isRelayed(ip):
    """Return a true or false value indicating the RELAYCLIENT setting in
    the access db.
    """
    if getSmtpaccessVal('RELAYCLIENT', ip) is None:
        return 0
    else:
        return 1


def isWhiteblocked(ip):
    """Return a true or false value indicating the BLOCK setting in the
    access db.

    If the client ip is specifically whitelisted from blocks in the
    smtpaccess database, the return value will be true.  If the ip is
    not listed, or the value in the database is not '', the return
    value will be false.

    """
    if getSmtpaccessVal('BLOCK', ip) is '':
        return 1
    else:
        return 0


def getBlockVal(ip):
    """Return the value of the BLOCK setting in the access db.

    The value will either be None, '', or another string which will be
    sent back to a client to indicate that mail will not be accepted
    from them.  The values None and '' indicate that the client is not
    blocked.  The value '' indicates that the client is specifically
    whitelisted from blocks.

    """
    return getSmtpaccessVal('BLOCK', ip)
