#!/usr/bin/python

import sys
import string
import thread
import time

# The rate is measured in messages / interval in minutes
max_connections = 60
interval = 1

# Keep a dictionary of authenticated senders to avoid more work than
# required.
senders_lock = thread.allocate_lock()
senders = {}

# The senders lists will be scrubbed at the interval indicated in
# seconds.  All records older than the "listed_for" number of seconds
# will be removed from the lists.
senders_last_purged = time.time()
senders_listed_for = 604800
senders_purge_interval = 43200

# Record in the system log that this filter was initialized.
sys.stderr.write( 'Initialized the ratelimit python filter\n' )



def dofilter( message_body, message_ctrl_files ):
    """
    Search through the control files until the "Received-From-MTA" record
    is found.
    Check how many times this server has connected recently, and decide to
    accept or reject the message.
    """

    global senders_last_purged

    try:
        # Open the first file, read lines until we find one that
        # begins with 'f'.
        ctlfile = open( message_ctrl_files[0] )
        ctlline = ctlfile.readline()
        while ctlline:
            if ctlline[0] == 'f':
                break
            ctlline.readline()
    except:
        return '451 Internal failure locating control files'

    # Treat a missing record as a non-fatal error
    if ctlline == '':
        return ''
    # Null sender is allowed as a non-fatal error
    if len( ctlline ) == 2:
        return ''

    # The sender's addres follows the ';' character
    senderi = string.index( ctlline, ';' )
    sender = string.strip( ctlline[senderi:] )

    senders_lock.acquire()

    # Scrub the lists if it is time to do so.
    if time.time() > (senders_last_purged + senders_purge_interval):
        min_age = time.time() - senders_listed_for
        pass  ## FIXME
        senders_last_purged = time.time()

    current_time = int(time.time() / 60)

    # If this is the first connection, prepare a rate tracker
    # Otherwise, mark the number of connections during the last interval.
    if not senders.has_key( sender ):
        senders[ sender ] = { current_time: 1 }
    elif not senders[ sender ].has_key( current_time ):
        senders[ sender ][ current_time ] = 1
    else:
        senders[ sender ][ current_time ] = senders[ sender ][ current_time ] + 1

    if senders[ sender ][ current_time ] > max_connections:
        status = '421 Too many messages from %s, slow down.' % sender
    else:
        status = ''

    senders_lock.release()

    return status
