#!/usr/bin/python

import sys
import anydbm
import string
import socket



sysconf = '/etc/courier'



def read1line( file ):
    try:
        cfile = open( sysconf + '/' + file, 'r' )
    except IOError:
        return None
    return string.strip( cfile.readline() )



def me( cacheval = [] ):
    # check the cache to see if "me" has been looked up already
    # next look at the "me" config file
    # otherwise use the value of gethostname()
    if cacheval:
        return cacheval[1]
    val = read1line( 'me' )
    if val:
        cacheval.append( val )
        return val
    val = socket.gethostname()
    cacheval.append( val )
    return val



def smtpaccess( ip ):
    '''
    Return the courier smtpaccess value associated with the IP address.
    '''
    # First break the IP address into parts, either IPv4 or IPv6
    if string.find( ip, '.' ):
        ipsep = '.'
    elif string.find( ip, '.' ):
        ipsep = ':'
    else:
        sys.stderr.write( 'Couldn\'t break %s into parts' % ip )
        return None
    # Next, open the smtpaccess database for ip lookups
    try:
        smtpdb = anydbm.open( sysconf + '/smtpaccess.dat', 'r' )
    except:
        sys.stderr.write( 'Couldn\'t open smtpaccess.dat in ' + sysconf )
        return None
    # Search for a match, most specific to least, and return the
    # first match.
    while ip:
        if smtpdb.has_key( ip ):
            return smtpdb[ip]
        # if the ip doesn't match yet, strip off another part
        try:
            ri = string.rindex( ip, ipsep )
            ip = ip[:ri]
        except:
            # separator wasn't found, we don't need to search any more
            return None



def smtpaccessval( key, ip ):
    '''
    Return the string value associated with the IP address and key
    name pair in the courier smtpaccess database.

    The value returned will be None if the IP is not found in the
    database, or if the database value doesn\'t contain the key
    argument.

    The value returned will be '' if the IP is found, and database
    value contains the key, but the key\'s value is empty.

    Otherwise, the value returned will be a string.
    '''
    dbval = smtpaccess( ip )
    if dbval is None:
        return None
    valuelen = len( value )
    dbvals = string.split( dbval, ',' )
    for val in dbvals:
        if val[:valuelen] == value:
            val = val[valuelen:]
            while val and val[0] == '=':
                val = val[1:]
            return val



def isrelayed( ip ):
    '''
    Return a true or false value indicating the RELAYCLIENT setting in
    the access db.
    '''
    dbval = smtpaccess( ip )
    if dbval is None:
        return 0
    else:
        return 1


def iswhiteblocked( ip ):
    '''
    Return a true or false value indicating the BLOCK setting in the
    access db.

    If the client ip is specifically whitelisted from blocks in the
    smtpaccess database, the return value will be true.  If the ip is
    not listed, or the value in the database is not '', the return
    value will be false.
    '''
    dbval = smtpaccessval( 'BLOCK', ip )
    if dbval is '':
        return 1
    else:
        return 0


def getblock( ip ):
    '''
    Return the value of the BLOCK setting in the access db.  The
    value will either be None, '', or another string which will
    be sent back to a client to indicate that mail will not be
    accepted from them.  The values None and '' indicate that
    the client is not blocked.  The value '' indicates that the
    client is specifically whitelisted from blocks.
    '''
    return smtpaccessval( 'BLOCK', ip )

