#!/usr/bin/python

import string
import re



def get_sender( controlfile ):
    # Search for the sender record
    controlfile.seek( 0 )
    ctlline = controlfile.readline()
    while ctlline:
        if ctlline[0] == 'f':
            break
        ctlline = controlfile.readline()
    # Treat a missing record as a non-fatal error
    if ctlline == '':
        return None
    # Null sender is allowed as a non-fatal error
    if len( ctlline ) == 2:
        return None

    # The sender's address follows the ';' character
    senderi = string.index( ctlline, ';' )
    sender = string.strip( ctlline[senderi:] )

    return sender



sender_ipv4_re = re.compile( '\[(?:::ffff:)?(\d*.\d*.\d*.\d*)\]' )
sender_ipv6_re = re.compile( '\[([0-9a-f:]*)\]' )
def get_senders_ip( controlfile ):
    sender = get_sender( controlfile )
    if not sender:
        return sender
    rematch = sender_ipv4_re.search( sender )
    if rematch.group(1):
        return rematch.group(1)
    # else, we probably have an IPv6 address
    rematch = sender_ipv6_re.search( sender )
    return rematch.group(1)

