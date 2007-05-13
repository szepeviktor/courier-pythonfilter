#!/usr/bin/python
# courier.config -- python module for Courier configuration access
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

import os
import sys
import anydbm
import string
import socket


prefix = '/usr/lib/courier'
exec_prefix = '/usr/lib/courier'
bindir = '/usr/lib/courier/bin'
sbindir = '/usr/lib/courier/sbin'
libexecdir = '/usr/lib/courier/libexec'
sysconfdir = '/etc/courier'
datadir = '/usr/lib/courier/share'
localstatedir = '/var/spool/courier'
mailuser = 'daemon'
mailgroup = 'daemon'
mailuid = '2'
mailgid = '2'


def _setup():
    (chIn, chOut) = os.popen4('courier-config')
    chOutLine = chOut.readline()
    while chOutLine != '':
        try:
            (setting, valueN) = chOutLine.split('=', 1)
            value = valueN.strip()
        except:
            chOutLine = chOut.readline()
            continue
        if setting in ('prefix', 'exec_prefix', 'bindir', 'sbindir', 
                       'libexecdir', 'sysconfdir', 'datadir', 'localstatedir', 
                       'mailuser', 'mailgroup', 'mailuid', 'mailgid'):
            globals()[setting] = value
        chOutLine = chOut.readline()


def read1line(file):
    try:
        cfile = open(sysconfdir + '/' + file, 'r')
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


def defaultdomain(_cached = [None]):
    """Return Courier's "defaultdomain" value.

    Call this function with no arguments.

    """
    # check the cache to see if "defaultdomain" has been looked up already
    # next look at the "defaultdomain" config file
    # otherwise use the value of me()
    if _cached[0]:
        return _cached[0]
    val = read1line('defaultdomain')
    if val:
        _cached[0] = val
        return val
    return me()


def dsnfrom(_cached = [None]):
    """Return Courier's "dsnfrom" value.

    Call this function with no arguments.

    """
    if _cached[0]:
        return _cached[0]
    val = read1line('dsnfrom')
    if val:
        _cached[0] = val
        return val
    return '"Courier mail server at %s" <@>' % me()


def locallowercase():
    """Return True if the locallowercase file exists, and False otherwise."""
    if os.access('%s/locallowercase' % sysconfdir, os.F_OK):
        return 1
    return 0


def isLocal(domain):
    """Return True if domain is "local", and False otherwise.

    See the courier(8) man page for more information on local domains.

    """
    try:
        locals = open('%s/locals' % sysconfdir)
    except IOError:
        if domain == me():
            return 1
        return 0
    for line in locals.readlines():
        if line[0] in '#\n':
            continue
        line = string.strip(line)
        if line[0] == '!' and line[1:] == domain:
            return 0
        if line[0] == '.' and line == domain[-(len(line)):]:
            return 1
        if line == domain:
            return 1
    return 0


def isHosteddomain(domain):
    """Return True if domain is a hosted domain, and False otherwise.

    See the courier(8) man page for more information on hosted domains.

    """
    try:
        hosteddomains = anydbm.open('%s/hosteddomains.dat' % sysconfdir, 'r')
    except anydbm.error:
        return 0
    if hosteddomains.has_key(domain):
        return 1
    parts = string.split(domain, '.')
    for x in range(1, len(parts)):
        domainSub = '.' + string.join(parts[x:], '.')
        if hosteddomains.has_key(domainSub):
            return 1
    return 0


def getAlias(address):
    """Return a list of addresses to which the address argument will expand.

    If no alias matches the address argument, None will be returned.

    """
    if '@' in address:
        atIndex = string.index(address, '@')
        domain = address[atIndex + 1:]
        if isLocal(domain):
            address = '%s@%s' % (address[:atIndex], me())
    else:
        address = '%s@%s' % (address, me())
    try:
        aliases = anydbm.open('%s/aliases.dat' % sysconfdir, 'r')
    except anydbm.error:
        return None
    if aliases.has_key(address):
        alias = string.strip(aliases[address])
        return string.split(alias, '\n')
    return None


def smtpaccess(ip):
    """ Return the courier smtpaccess value associated with the IP address."""
    # First break the IP address into parts, either IPv4 or IPv6
    if '.' in  ip:
        ipsep = '.'
    elif ':' in ip:
        ipsep = ':'
    else:
        sys.stderr.write('Couldn\'t break %s into parts\n' % ip)
        return None
    # Next, open the smtpaccess database for ip lookups
    try:
        smtpdb = anydbm.open(sysconfdir + '/smtpaccess.dat', 'r')
    except:
        sys.stderr.write('Couldn\'t open smtpaccess.dat in %s\n' % sysconfdir)
        return None
    # Search for a match, most specific to least, and return the
    # first match.
    while ip:
        if ipsep == '.' and smtpdb.has_key(ip):
            return smtpdb[ip]
        elif ipsep == ':' and smtpdb.has_key(':' + ip):
            return smtpdb[':' + ip]
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


# Call _setup to correct the module path values
_setup()
