#!/usr/bin/python

import string
import re



def get_lines( controlfile, key ):
    '''
    Search through the control file, return a list of lines beginning
    with the key.  "key" should be a one character string.
    '''
    lines = []
    # Search for the recipient records
    controlfile.seek( 0 )
    ctlline = controlfile.readline()
    while ctlline:
        if ctlline[0] == key:
            lines.append( string.strip(ctlline[1:]) )
        ctlline = controlfile.readline()

    return lines



def get_senders_mta( controlfile ):
    # Search for the "received-from-mta" record
    senderlines = get_lines( controlfile, 'f' )
    if senderlines:
        return senderlines[0]
    else:
        return None



sender_ipv4_re = re.compile( '\[(?:::ffff:)?(\d*.\d*.\d*.\d*)\]' )
sender_ipv6_re = re.compile( '\[([0-9a-f:]*)\]' )
def get_senders_ip( controlfile ):
    sender = get_senders_mta( controlfile )
    if not sender:
        return sender
    rematch = sender_ipv4_re.search( sender )
    if rematch.group(1):
        return rematch.group(1)
    # else, we probably have an IPv6 address
    rematch = sender_ipv6_re.search( sender )
    return rematch.group(1)



def get_sender( controlfile ):
    senderlines = get_lines( controlfile, 's' )
    if senderlines:
        return senderlines[0]
    else:
        return None



def get_recipients( controlfile ):
    return get_lines( controlfile, 'r' )


